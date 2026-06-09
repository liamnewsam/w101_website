"""PPO training loop for the W101 card game.

Usage:
    cd back_end
    # Round 1 (fresh training)
    python -m rl.train --school Fire

    # Round 2 (resume + trained opponents + lower BC)
    python -m rl.train --school Fire \\
        --checkpoint rl/checkpoints/checkpoints/Fire/latest.pt \\
        --reset-optimizers \\
        --opponents Storm,Ice \\
        --bc-coef 0.15 \\
        --log rl/logs/logs/Fire_round2.csv

Checkpoints are saved to rl/checkpoints/{school}/ every ``save_every`` iterations.
"""

from __future__ import annotations

import argparse
import csv
import os
import random as _random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List

import numpy as np
import torch
import torch.nn.functional as F

from rl.env import (
    W101Env,
    CARD_DIM, PLAYER_DIM, GAME_DIM,
    EFFECT_TOKEN_DIM, MAX_EFFECT_TOKENS,
    HAND_SIZE, MAX_PLAYERS, MAX_TOTAL_CARDS, N_TARGET_SLOTS, N_PIP_SCHOOL_ACTIONS, N_ACTIONS,
)
from rl.model import TransformerActorCritic
from rl.deck_builder import (
    DeckBuilderNet, DeckBuilderBuffer, select_deck, ppo_update_deck_builder,
    compute_bc_loss, deck_to_card_ids, deck_to_pool_indices, make_school_bias_vec,
)
from rl.opponent import load_opponent

from Deck import *

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

def random_moderate_bot():
    school = random.choice(SCHOOL_DECK_ORDER)
    deck = DECK_MASTER["moderate"][school]()
    return {"level": 100, "school": school, "deck": deck}

@dataclass
class Config:
    # Environment
    agent_school: str  = "Fire"
    agent_level:  int  = 100
    allies:       list = None
    enemies:      list = field(default_factory=lambda: [random_moderate_bot()])
    max_turns:    int  = 100

    # Model
    embed_dim: int = 128
    n_heads:   int = 4
    n_layers:  int = 3

    # PPO hypers
    lr:              float = 5e-5
    gamma:           float = 0.99
    lam:             float = 0.95
    clip_eps:        float = 0.2
    vf_coef:         float = 0.25
    ent_coef:             float = 0.01
    deck_builder_ent_coef: float = 0.01
    max_grad_norm:   float = 0.5
    n_epochs:        int   = 2
    batch_size:      int   = 32

    # Training schedule
    rollout_steps: int = 4096
    n_iterations:  int = 1000
    save_every:    int = 50

    # Deck builder
    deck_builder_embed_dim: int   = 128
    deck_builder_n_heads:   int   = 4
    deck_builder_n_layers:  int   = 4
    deck_builder_lr:        float = 2.5e-4
    deck_update_freq:           int   = 20   # update deck builder every N completed games
    school_bias:                float = 1.0  # logit bonus for in-school cards
    cross_school_bias:          float = 1.0  # logit bonus for cheap off-school cards (disabled — let PPO decide)
    cross_school_pip_threshold: int   = 3    # pip cost threshold for cross-school bonus
    damage_card_bias:           float = 0.5  # extra logit bonus for damage/DoT/drain cards
                                             # counters 0-pip utility card over-selection

    # Deck builder behavioural cloning
    bc_deck:  object = None   # Deck to clone; None → moderate agent-school deck
    bc_coef:  float  = 0.15   # weight of BC loss relative to PPO loss (phase 2 steady state)
    # Phase 2 BC annealing: bc_coef starts at bc_coef_phase2_start and decays linearly
    # to bc_coef over bc_coef_anneal_iters iterations. Keeps early phase-2 decks close to
    # the familiar phase-1 deck, preventing the cold-start performance cliff.
    bc_coef_phase2_start:  float = 0.9   # initial BC weight at phase 2 start
    bc_coef_anneal_iters:  int   = 100   # iters to decay from start to bc_coef

    # Cards always included in every deck (e.g. ["reshuffle"] for Life)
    forced_deck_cards: list = field(default_factory=list)

    # Evolutionary deck builder (replaces PPO deck builder when True)
    use_evo_deck:      bool   = False
    evo_pop_size:      int    = 15
    evo_n_elite:       int    = 7
    evo_mutation_rate: float  = 0.15
    evo_gen_games:        int    = 240  # games across population before evolving
    evo_elite_reset_gens: int    = 5    # reset elite stats every N generations
    evo_seed_deck:        object = None  # Deck to seed population from; None → random init

    # Phase-1/2 progressive training
    pin_deck:             bool  = False  # Phase 1: fix deck to evo_seed_deck every game, skip deck builder
    phase1_wr_threshold:  float = 0.0   # smoothed WR to advance between phase-1 sub-phases (0 → use phase2)
    phase2_wr_threshold:  float = 0.0   # smoothed WR to enter phase 2 / evo from final sub-phase (0 = transition as soon as window fills)
    phase2_evo_gen_games: int   = 240   # gen_games for the evo builder when phase 2 begins
    n_curriculum_phases:  int   = 1     # number of sub-phases in phase 1; enemy level = subphase*100/n
    # Deck augmentation during phase 1: fraction of fixed-deck cards randomly swapped each game.
    # Forces the policy to generalise across deck variants rather than memorising one specific deck.
    phase1_deck_swap_rate: float = 0.25  # 0 = disabled;
    # Phase 2 warmup: use the fixed (moderate) deck for this many iterations at the start of
    # phase 2, while the deck builder trains purely on BC in the background. Prevents deploying
    # random deck-builder selections before the model has converged.
    phase2_warmup_iters:      int   = 75
    phase2_warmup_bc_epochs:  int   = 10   # BC epochs per warmup iter (more than n_epochs to converge faster)

    # Early stopping
    patience:              int = 200  # iters without smoothed-WR improvement; 0 = disabled
    early_stop_smoothing:  int = 20   # rolling window size for smoothed win rate

    # Resume
    resume_checkpoint: str | None = None  # path to a .pt checkpoint to load

    # Logging
    log_file: str | None = None  # CSV path; None → rl/logs/{school}_{timestamp}.csv

    # Self-play opponents.
    # Pass school names via --opponents; resolved to rl/checkpoints/checkpoints/{School}/latest.pt.
    # One opponent is sampled randomly each episode from the pool.
    opponent_schools: list = field(default_factory=list)

    # Resume
    reset_optimizers: bool = False  # load model weights only, discard Adam state

    device: str = "cuda" if torch.cuda.is_available() else "cpu"


# ──────────────────────────────────────────────────────────────────────────────
# Rollout buffer
# ──────────────────────────────────────────────────────────────────────────────

class RolloutBuffer:
    def __init__(self, capacity: int):
        self.capacity  = capacity
        self._ptr      = 0
        self.cards     = np.zeros((capacity, MAX_TOTAL_CARDS,   CARD_DIM),         dtype=np.float32)
        self.players   = np.zeros((capacity, MAX_PLAYERS,       PLAYER_DIM),       dtype=np.float32)
        self.effects   = np.zeros((capacity, MAX_EFFECT_TOKENS, EFFECT_TOKEN_DIM), dtype=np.float32)
        self.games     = np.zeros((capacity, GAME_DIM),                            dtype=np.float32)
        self.masks     = np.zeros((capacity, N_ACTIONS),                           dtype=np.float32)
        self.actions   = np.zeros(capacity,                                        dtype=np.int64)
        self.log_probs = np.zeros(capacity,                                        dtype=np.float32)
        self.rewards   = np.zeros(capacity,                                        dtype=np.float32)
        self.values    = np.zeros(capacity,                                        dtype=np.float32)
        self.dones     = np.zeros(capacity,                                        dtype=np.float32)

    def push(self, cards, players, effects, game, mask, action, log_prob, reward, value, done):
        i = self._ptr
        self.cards[i]     = cards
        self.players[i]   = players
        self.effects[i]   = effects
        self.games[i]     = game
        self.masks[i]     = mask
        self.actions[i]   = action
        self.log_probs[i] = log_prob
        self.rewards[i]   = reward
        self.values[i]    = value
        self.dones[i]     = float(done)
        self._ptr        += 1

    @property
    def full(self):
        return self._ptr >= self.capacity

    def compute_gae(self, last_value: float, gamma: float, lam: float):
        n    = self._ptr
        adv  = np.zeros(n, dtype=np.float32)
        gae  = 0.0
        for t in reversed(range(n)):
            next_val  = last_value if t == n - 1 else self.values[t + 1]
            non_term  = 1.0 - self.dones[t]
            delta     = self.rewards[t] + gamma * next_val * non_term - self.values[t]
            gae       = delta + gamma * lam * non_term * gae
            adv[t]    = gae
        returns = adv + self.values[:n]
        return adv, returns

    def tensors(self, device):
        n = self._ptr
        return (
            torch.as_tensor(self.cards[:n],     device=device),
            torch.as_tensor(self.players[:n],   device=device),
            torch.as_tensor(self.effects[:n],   device=device),
            torch.as_tensor(self.games[:n],     device=device),
            torch.as_tensor(self.masks[:n],     device=device),
            torch.as_tensor(self.actions[:n],   device=device),
            torch.as_tensor(self.log_probs[:n], device=device),
        )

    def clear(self):
        self._ptr = 0


# ──────────────────────────────────────────────────────────────────────────────
# Reward normalizer
# ──────────────────────────────────────────────────────────────────────────────

class RunningMeanStd:
    """Online Welford estimator — divides rewards by running std to fix critic collapse."""
    def __init__(self):
        self.mean  = 0.0
        self.var   = 1.0
        self.count = 0

    def update(self, x: np.ndarray):
        n     = len(x)
        delta = x.mean() - self.mean
        total = self.count + n
        self.mean  += delta * n / total
        m_a         = self.var * self.count
        m_b         = x.var() * n
        self.var    = (m_a + m_b + delta ** 2 * self.count * n / total) / total
        self.count  = total

    def normalize(self, x: np.ndarray) -> np.ndarray:
        return x / (np.sqrt(self.var) + 1e-8)


# ──────────────────────────────────────────────────────────────────────────────
# PPO update
# ──────────────────────────────────────────────────────────────────────────────

def ppo_update(
    model:     TransformerActorCritic,
    optimizer: torch.optim.Optimizer,
    buffer:    RolloutBuffer,
    last_value: float,
    cfg:       Config,
):
    adv, returns = buffer.compute_gae(last_value, cfg.gamma, cfg.lam)

    adv_t = torch.as_tensor(adv,     device=cfg.device)
    ret_t = torch.as_tensor(returns, device=cfg.device)
    adv_t = (adv_t - adv_t.mean()) / (adv_t.std() + 1e-8)

    cards, players, effects, games, masks, actions, old_log_probs = buffer.tensors(cfg.device)
    n = len(actions)

    pg_losses, vf_losses, ent_losses = [], [], []

    for _ in range(cfg.n_epochs):
        idxs = torch.randperm(n, device=cfg.device)
        for start in range(0, n, cfg.batch_size):
            b = idxs[start : start + cfg.batch_size]

            log_probs, values, entropy = model.evaluate(
                cards[b], players[b], effects[b], games[b], masks[b], actions[b]
            )

            ratio  = torch.exp(log_probs - old_log_probs[b])
            adv_b  = adv_t[b]

            pg_loss = -torch.min(
                ratio * adv_b,
                ratio.clamp(1 - cfg.clip_eps, 1 + cfg.clip_eps) * adv_b,
            ).mean()

            vf_loss  = F.mse_loss(values, ret_t[b])
            ent_loss = -entropy.mean()

            loss = pg_loss + cfg.vf_coef * vf_loss + cfg.ent_coef * ent_loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.max_grad_norm)
            optimizer.step()

            pg_losses.append(pg_loss.item())
            vf_losses.append(vf_loss.item())
            ent_losses.append(-ent_loss.item())

    return {
        "pg_loss": float(np.mean(pg_losses)),
        "vf_loss": float(np.mean(vf_losses)),
        "entropy": float(np.mean(ent_losses)),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Training loop
# ──────────────────────────────────────────────────────────────────────────────

CSV_FIELDS = [
    "iteration", "phase", "enemy_level", "episodes", "win_rate", "mean_reward",
    "pg_loss", "vf_loss", "entropy", "sps",
    "db_pg", "db_vf", "db_ent", "db_bc",
]

def train(cfg: Config = Config()):
    os.makedirs("rl/checkpoints", exist_ok=True)
    os.makedirs("rl/logs",        exist_ok=True)
    device = torch.device(cfg.device)

    log_path = cfg.log_file or f"rl/logs/{cfg.agent_school}_{int(time.time())}.csv"
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    _log_f   = open(log_path, "w", newline="")
    _csv     = csv.DictWriter(_log_f, fieldnames=CSV_FIELDS)
    _csv.writeheader()
    print(f"  → logging to {log_path}")

    # Build pool covering all 7 schools.
    # Schools listed in opponent_schools use their trained policy;
    # the rest use a fresh moderate bot.
    ALL_SCHOOLS = ["Fire", "Ice", "Storm", "Life", "Death", "Myth", "Balance"]
    trained = set(cfg.opponent_schools)
    opponent_pool: list[tuple[dict, object]] = []  # (enemy_cfg, policy | None)
    for school in ALL_SCHOOLS:
        if school in trained:
            # rl/checkpoints/{school}/ works in Modal (symlink resolves correctly);
            # rl/checkpoints/checkpoints/{school}/ is the path after a local volume sync.
            ckpt_path = f"rl/checkpoints/{school}/latest.pt"
            if not os.path.exists(ckpt_path):
                ckpt_path = f"rl/checkpoints/checkpoints/{school}/latest.pt"
            policy, enemy_cfg = load_opponent(ckpt_path, cfg.device, cfg.max_turns)
            if policy is not None:
                opponent_pool.append((enemy_cfg, policy))
                print(f"  → loaded trained {school} opponent from {ckpt_path}")
            else:
                print(f"  → WARNING: {school} checkpoint not found, falling back to moderate bot")
                deck = DECK_MASTER["moderate"][school]()
                opponent_pool.append(({"school": school, "level": 100, "deck": deck}, None))
        else:
            deck = DECK_MASTER["moderate"][school]()
            opponent_pool.append(({"school": school, "level": 100, "deck": deck}, None))

    _subphase           = 1
    current_enemy_level = (_subphase * 100) // max(cfg.n_curriculum_phases, 1) if cfg.pin_deck else 100

    def _sample_opponent():
        """Pick a random school from the full pool; use trained policy if available."""
        enemy_cfg_base, policy = opponent_pool[_random.randrange(len(opponent_pool))]
        if cfg.pin_deck:
            enemy_cfg = dict(enemy_cfg_base)
            enemy_cfg["level"] = current_enemy_level
        else:
            enemy_cfg = enemy_cfg_base
        policies = [policy] if policy is not None else []
        return [enemy_cfg], policies

    init_enemies, init_policies = _sample_opponent()
    opponent_policies = init_policies

    env = W101Env(
        agent_school=cfg.agent_school,
        agent_level=cfg.agent_level,
        agent_deck=None,
        allies=cfg.allies,
        enemies=init_enemies,
        max_turns=cfg.max_turns,
        opponent_policies=init_policies,
    )

    model = TransformerActorCritic(
        card_dim             = CARD_DIM,
        player_dim           = PLAYER_DIM,
        game_dim             = GAME_DIM,
        effect_token_dim     = EFFECT_TOKEN_DIM,
        hand_size            = HAND_SIZE,
        max_players          = MAX_PLAYERS,
        max_total_cards      = MAX_TOTAL_CARDS,
        max_effect_tokens    = MAX_EFFECT_TOKENS,
        n_target_slots       = N_TARGET_SLOTS,
        n_pip_school_actions = N_PIP_SCHOOL_ACTIONS,
        embed_dim            = cfg.embed_dim,
        n_heads              = cfg.n_heads,
        n_layers             = cfg.n_layers,
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    buffer    = RolloutBuffer(cfg.rollout_steps)

    if cfg.use_evo_deck:
        from rl.evo_deck import EvoDecBuilder
        # Resolve seed deck: explicit cfg.evo_seed_deck → moderate school deck
        if cfg.evo_seed_deck is not None:
            _evo_seed = deck_to_pool_indices(cfg.evo_seed_deck)
        else:
            _evo_seed = None
        evo_builder = EvoDecBuilder(
            school            = cfg.agent_school,
            pop_size          = cfg.evo_pop_size,
            n_elite           = cfg.evo_n_elite,
            mutation_rate     = cfg.evo_mutation_rate,
            school_bias       = cfg.school_bias,
            gen_games         = cfg.evo_gen_games,
            forced_cards      = cfg.forced_deck_cards or None,
            seed_deck         = _evo_seed,
            elite_reset_gens  = cfg.evo_elite_reset_gens,
        )
        deck_builder   = None
        deck_optimizer = None
        deck_buffer    = None
    else:
        evo_builder = None
        deck_builder = DeckBuilderNet(
            embed_dim = cfg.deck_builder_embed_dim,
            n_heads   = cfg.deck_builder_n_heads,
            n_layers  = cfg.deck_builder_n_layers,
        ).to(device)
        deck_optimizer = torch.optim.Adam(deck_builder.parameters(), lr=cfg.deck_builder_lr)
        deck_buffer    = DeckBuilderBuffer(capacity=cfg.deck_update_freq)

    last_db_metrics: dict = {}
    school_bias_vec = make_school_bias_vec(
        cfg.agent_school, cfg.school_bias,
        cfg.cross_school_bias, cfg.cross_school_pip_threshold,
        cfg.damage_card_bias, cfg.device,
    )

    current_traj: dict | None = None

    # ── resume from checkpoint ────────────────────────────────────────────────
    if cfg.resume_checkpoint:
        ckpt = torch.load(cfg.resume_checkpoint, map_location=device)
        saved_state  = ckpt["model"]
        model_state  = model.state_dict()
        compatible   = {k: v for k, v in saved_state.items()
                        if k in model_state and v.shape == model_state[k].shape}
        skipped      = model_state.keys() - compatible.keys()
        model.load_state_dict(compatible, strict=False)
        if skipped:
            print(f"  → re-initialized {len(skipped)} layer(s) (shape mismatch — critic enlarged): "
                  + ", ".join(sorted(skipped)))
        if cfg.use_evo_deck:
            if ckpt.get("evo_state"):
                evo_builder.load_state_dict(ckpt["evo_state"])
                print(f"  → resumed evo population gen {evo_builder.generation}")
        elif ckpt.get("deck_builder"):
            deck_builder.load_state_dict(ckpt["deck_builder"])
            if not cfg.reset_optimizers:
                if ckpt.get("optimizer"):      optimizer.load_state_dict(ckpt["optimizer"])
                if ckpt.get("deck_optimizer"): deck_optimizer.load_state_dict(ckpt["deck_optimizer"])
        suffix = " (weights only — optimizers reset)" if cfg.reset_optimizers else ""
        print(f"  → resumed {cfg.resume_checkpoint} (iter {ckpt['iteration']}){suffix}")

    # ── BC target deck ────────────────────────────────────────────────────────
    # Priority: explicit cfg.bc_deck → checkpoint's saved deck → moderate school deck
    if cfg.bc_deck is not None:
        _bc_source = cfg.bc_deck
    elif cfg.resume_checkpoint and ckpt.get("deck_card_ids"):
        from rl.deck_builder import deck_from_card_ids
        _bc_source = deck_from_card_ids(ckpt["deck_card_ids"])
        print(f"  → BC reference: agent's checkpoint deck ({len(ckpt['deck_card_ids'])} cards)")
    else:
        _bc_source = DECK_MASTER["moderate"][cfg.agent_school]()
        print(f"  → BC reference: moderate {cfg.agent_school} deck")
    bc_deck_indices = deck_to_pool_indices(_bc_source)

    # Fixed deck for phase 1: prefer explicit evo_seed_deck, else moderate school deck
    _fixed_deck = cfg.evo_seed_deck or DECK_MASTER["moderate"][cfg.agent_school]()

    # Build a pool of in-school cards for phase 1 deck augmentation
    if cfg.pin_deck and cfg.phase1_deck_swap_rate > 0:
        from rl.deck_builder import _get_all_pool
        from Card import Card as _Card
        _pool_cards, _ = _get_all_pool()
        _school_pool = [cd for cd in _pool_cards if cd.school.lower() == cfg.agent_school.lower()]
    else:
        _school_pool = []

    def _augment_fixed_deck():
        """Return _fixed_deck with a random fraction of cards swapped from the school pool."""
        if not _school_pool or cfg.phase1_deck_swap_rate <= 0:
            return _fixed_deck
        from Card import Card as _Card
        base_cards = list(_fixed_deck.cards)
        n_swap = sum(1 for _ in range(len(base_cards)) if _random.random() < cfg.phase1_deck_swap_rate)
        if n_swap == 0:
            return _fixed_deck
        swap_indices = _random.sample(range(len(base_cards)), n_swap)
        new_cards = list(base_cards)
        for idx in swap_indices:
            new_cards[idx] = _Card(_random.choice(_school_pool))
        from Deck import Deck as _Deck
        return _Deck(_fixed_deck.name, new_cards)

    if cfg.pin_deck:
        _p1_thr = cfg.phase1_wr_threshold or cfg.phase2_wr_threshold
        print(f"  → Phase 1 sub-phase {_subphase}/{cfg.n_curriculum_phases} "
              f"(enemy level {current_enemy_level}): "
              f"sub-phase threshold {_p1_thr:.2f}, phase-2 threshold {cfg.phase2_wr_threshold:.2f}")

    if cfg.pin_deck:
        new_deck     = _augment_fixed_deck()
        current_traj = None
    elif cfg.use_evo_deck:
        new_deck, _deck_idx = evo_builder.get_eval_deck()
        current_traj = {"deck_idx": _deck_idx}
    elif _phase2_iter <= cfg.phase2_warmup_iters:
        new_deck     = _fixed_deck
        current_traj = None
    else:
        new_deck, current_traj = select_deck(
            deck_builder, cfg.agent_school, cfg.device, school_bias=cfg.school_bias,
            cross_school_bias=cfg.cross_school_bias,
            damage_card_bias=cfg.damage_card_bias,
            cross_school_pip_threshold=cfg.cross_school_pip_threshold,
            forced_cards=cfg.forced_deck_cards or None,
        )
    env.agent_deck = new_deck
    obs, _      = env.reset()
    ep_reward        = 0.0
    ep_rewards: List[float] = []
    ep_wins          = 0
    deck_buffer_wins = 0
    global_step      = 0
    t0               = time.time()

    wr_history             = deque(maxlen=cfg.early_stop_smoothing)
    best_smoothed_wr       = 0.0
    iters_no_improvement   = 0
    _phase2_iter           = 0   # counts iterations spent in phase 2 (for BC annealing)

    for iteration in range(1, cfg.n_iterations + 1):
        model.eval()
        buffer.clear()

        # Anneal BC coef in phase 2: start high (near phase-1 deck) and decay to cfg.bc_coef
        if not cfg.pin_deck and not cfg.use_evo_deck:
            _phase2_iter += 1
            if _phase2_iter == cfg.phase2_warmup_iters + 1:
                print(f"  → Phase 2 warmup complete — deck builder now selecting decks")
            t = min(1.0, (_phase2_iter - 1) / max(1, cfg.bc_coef_anneal_iters))
            _effective_bc_coef = cfg.bc_coef_phase2_start + (cfg.bc_coef - cfg.bc_coef_phase2_start) * t
            cfg.bc_coef = _effective_bc_coef

        while not buffer.full:
            cards   = torch.as_tensor(obs["cards"][None],        device=device)
            players = torch.as_tensor(obs["players"][None],      device=device)
            effects = torch.as_tensor(obs["effects"][None],      device=device)
            game    = torch.as_tensor(obs["game"][None],         device=device)
            mask    = torch.as_tensor(obs["action_mask"][None],  device=device)

            action, log_prob, value = model.act(cards, players, effects, game, mask)
            action_np = int(action.item())

            obs_next, reward, done, truncated, _ = env.step(action_np)
            ep_reward   += reward
            global_step += 1

            buffer.push(
                obs["cards"], obs["players"], obs["effects"], obs["game"], obs["action_mask"],
                action_np, float(log_prob.item()), reward,
                float(value.item()), done or truncated,
            )

            obs = obs_next
            if done or truncated:
                ep_rewards.append(ep_reward)
                if env.game.winner == "A":
                    ep_wins += 1
                ep_reward = 0.0

                # ── deck builder update ───────────────────────────────────────
                terminal_r = (1.0 if env.game.winner == "A"
                              else -1.0 if env.game.winner == "B"
                              else 0.0)
                if current_traj is not None:
                    if cfg.use_evo_deck:
                        evo_builder.record_outcome(current_traj["deck_idx"], terminal_r > 0)
                        if evo_builder.ready_to_evolve:
                            last_db_metrics = evo_builder.evolve()
                    else:
                        deck_buffer.push_episode(
                            current_traj["pool_obs"], current_traj["masks"],
                            current_traj["actions"],  current_traj["log_probs"],
                            current_traj["values"],   terminal_r,
                        )
                        if terminal_r > 0:
                            deck_buffer_wins += 1
                        if deck_buffer.full:
                            last_db_metrics = ppo_update_deck_builder(
                                deck_builder, deck_optimizer, deck_buffer, cfg,
                                school_bias_vec=school_bias_vec,
                                bc_deck_indices=bc_deck_indices,
                                run_ppo=(deck_buffer_wins > 0),
                            )
                            deck_buffer.clear()
                            deck_buffer_wins = 0
                            deck_builder.eval()

                if cfg.pin_deck:
                    new_deck     = _augment_fixed_deck()
                    current_traj = None
                elif cfg.use_evo_deck:
                    new_deck, _deck_idx = evo_builder.get_eval_deck()
                    current_traj = {"deck_idx": _deck_idx}
                elif _phase2_iter <= cfg.phase2_warmup_iters:
                    # Warmup: keep the familiar deck while deck builder trains on BC only
                    new_deck     = _fixed_deck
                    current_traj = None
                else:
                    new_deck, current_traj = select_deck(
                        deck_builder, cfg.agent_school, cfg.device,
                        school_bias=cfg.school_bias,
                        cross_school_bias=cfg.cross_school_bias,
            damage_card_bias=cfg.damage_card_bias,
                        cross_school_pip_threshold=cfg.cross_school_pip_threshold,
                        forced_cards=cfg.forced_deck_cards or None,
                    )
                env.agent_deck = new_deck
                if opponent_pool:
                    env.enemies, env.opponent_policies = _sample_opponent()
                obs, _ = env.reset()

        # Bootstrap value for the last (possibly incomplete) episode
        with torch.no_grad():
            cards_   = torch.as_tensor(obs["cards"][None],        device=device)
            players_ = torch.as_tensor(obs["players"][None],      device=device)
            effects_ = torch.as_tensor(obs["effects"][None],      device=device)
            game_    = torch.as_tensor(obs["game"][None],         device=device)
            mask_    = torch.as_tensor(obs["action_mask"][None],  device=device)
            _, last_val = model(cards_, players_, effects_, game_, mask_)
            last_value  = float(last_val.item())

        # Clip rewards — naturally bounded at ±1, normalization destabilises sparse signals
        buffer.rewards[:buffer._ptr] = np.clip(buffer.rewards[:buffer._ptr], -1.0, 1.0)

        model.train()
        metrics = ppo_update(model, optimizer, buffer, last_value, cfg)

        # During phase 2 warmup: run BC-only deck builder updates so the model
        # converges toward the reference deck before its selections are deployed.
        if (not cfg.pin_deck and not cfg.use_evo_deck
                and _phase2_iter <= cfg.phase2_warmup_iters
                and deck_builder is not None):
            deck_builder.train()
            for _ in range(cfg.phase2_warmup_bc_epochs):
                bc_loss = compute_bc_loss(
                    deck_builder, bc_deck_indices, cfg.agent_school,
                    school_bias_vec, cfg.device,
                )
                deck_optimizer.zero_grad()
                (cfg.bc_coef * bc_loss).backward()
                torch.nn.utils.clip_grad_norm_(deck_builder.parameters(), cfg.max_grad_norm)
                deck_optimizer.step()
            deck_builder.eval()

        if ep_rewards:
            n_ep     = len(ep_rewards)
            win_rate = ep_wins / n_ep
            mean_r   = float(np.mean(ep_rewards))
            sps      = global_step / (time.time() - t0)
            if cfg.use_evo_deck:
                db_str = (f" | evo_wr {last_db_metrics['evo_best_wr']:.3f}"
                          f" div {last_db_metrics['evo_diversity']:.3f}"
                          f" gen {last_db_metrics['evo_gen']}"
                          if last_db_metrics else "")
            else:
                db_str = (f" | db_pg {last_db_metrics['db_pg']:+.4f}"
                          f" db_ent {last_db_metrics['db_ent']:.4f}"
                          f" db_bc {last_db_metrics['db_bc']:.4f}"
                          if last_db_metrics else "")
            _phase_str = f"p1-{_subphase}/{cfg.n_curriculum_phases}" if cfg.pin_deck else "p2"
            print(
                f"iter {iteration:4d} | "
                f"{_phase_str} lv{current_enemy_level} | "
                f"ep {n_ep:4d} | "
                f"win {win_rate:.2f} | "
                f"r {mean_r:+.3f} | "
                f"pg {metrics['pg_loss']:+.4f} | "
                f"vf {metrics['vf_loss']:.4f} | "
                f"ent {metrics['entropy']:.4f} | "
                f"sps {sps:.0f}"
                + db_str
            )
            _csv.writerow({
                "iteration":   iteration,
                "phase":       _phase_str,
                "enemy_level": current_enemy_level,
                "episodes":    n_ep,
                "win_rate":    round(win_rate, 4),
                "mean_reward": round(mean_r, 4),
                "pg_loss":     round(metrics["pg_loss"], 4),
                "vf_loss":     round(metrics["vf_loss"], 4),
                "entropy":     round(metrics["entropy"], 4),
                "sps":         round(sps, 1),
                "db_pg":       round(last_db_metrics.get("db_pg",  last_db_metrics.get("evo_best_wr",  0.0)), 4),
                "db_vf":       round(last_db_metrics.get("db_vf",  last_db_metrics.get("evo_worst_wr", 0.0)), 4),
                "db_ent":      round(last_db_metrics.get("db_ent", last_db_metrics.get("evo_diversity", 0.0)), 4),
                "db_bc":       round(last_db_metrics.get("db_bc",  last_db_metrics.get("evo_gen",       0.0)), 4),
            })
            _log_f.flush()
            ep_rewards.clear()
            ep_wins = 0

            # ── win-rate tracking (phase transition + early stopping) ─────────
            wr_history.append(win_rate)
            if len(wr_history) == cfg.early_stop_smoothing:
                smoothed_wr = float(np.mean(wr_history))

                # Phase 1 sub-phase advance or Phase 2 transition
                if cfg.pin_deck:
                    _p1_thr = cfg.phase1_wr_threshold or cfg.phase2_wr_threshold  # fallback for compat
                    _p2_thr = cfg.phase2_wr_threshold
                    _advancing   = (_subphase < cfg.n_curriculum_phases
                                    and _p1_thr > 0 and smoothed_wr >= _p1_thr)
                    _entering_p2 = (_subphase == cfg.n_curriculum_phases
                                    and (_p2_thr == 0 or smoothed_wr >= _p2_thr))

                if cfg.pin_deck and _advancing:
                    # Advance to the next curriculum sub-phase (higher enemy level)
                    _subphase           += 1
                    current_enemy_level  = (_subphase * 100) // cfg.n_curriculum_phases
                    wr_history.clear()
                    best_smoothed_wr     = 0.0
                    iters_no_improvement = 0
                    print(f"  → Phase 1 sub-phase {_subphase}/{cfg.n_curriculum_phases}: "
                          f"enemy level → {current_enemy_level} "
                          f"(smoothed WR {smoothed_wr:.3f} ≥ {_p1_thr:.3f})")
                elif cfg.pin_deck and _entering_p2:
                    # Save a snapshot of the policy at the end of phase 1
                    os.makedirs(f"rl/checkpoints/{cfg.agent_school}", exist_ok=True)
                    p1_path = f"rl/checkpoints/{cfg.agent_school}/phase1_final.pt"
                    torch.save({
                        "iteration":      iteration,
                        "smoothed_wr":    round(smoothed_wr, 4),
                        "model":          model.state_dict(),
                        "optimizer":      optimizer.state_dict(),
                        "deck_card_ids":  deck_to_card_ids(_fixed_deck),
                        "config": {
                            "agent_school": cfg.agent_school,
                            "agent_level":  cfg.agent_level,
                            "embed_dim":    cfg.embed_dim,
                            "n_heads":      cfg.n_heads,
                            "n_layers":     cfg.n_layers,
                        },
                    }, p1_path)
                    print(f"  → phase 1 final snapshot saved to {p1_path}")

                    # All sub-phases cleared → Phase 2 (deck builder, level 100)
                    cfg.pin_deck = False
                    if cfg.use_evo_deck:
                        from rl.evo_deck import EvoDecBuilder
                        evo_builder = EvoDecBuilder(
                            school           = cfg.agent_school,
                            pop_size         = cfg.evo_pop_size,
                            n_elite          = cfg.evo_n_elite,
                            mutation_rate    = cfg.evo_mutation_rate,
                            school_bias      = cfg.school_bias,
                            gen_games        = cfg.phase2_evo_gen_games,
                            forced_cards     = cfg.forced_deck_cards or None,
                            seed_deck        = deck_to_pool_indices(_fixed_deck),
                            elite_reset_gens = cfg.evo_elite_reset_gens,
                        )
                        deck_mode = "evo deck"
                    else:
                        deck_mode = "transformer deck builder"
                    wr_history.clear()
                    best_smoothed_wr     = 0.0
                    iters_no_improvement = 0
                    print(f"  → Phase 2: {deck_mode} enabled at level 100 "
                          f"(smoothed WR {smoothed_wr:.3f} ≥ {_p2_thr:.3f})")

                # Early stopping + best.pt — runs in phase 2 or in non-phased runs;
                # skipped while waiting for the phase 2 threshold
                elif cfg.patience > 0 and not (cfg.pin_deck and (cfg.phase1_wr_threshold or cfg.phase2_wr_threshold) > 0):
                    if smoothed_wr > best_smoothed_wr:
                        best_smoothed_wr     = smoothed_wr
                        iters_no_improvement = 0
                        os.makedirs(f"rl/checkpoints/{cfg.agent_school}", exist_ok=True)
                        best_path = f"rl/checkpoints/{cfg.agent_school}/best.pt"
                        if cfg.use_evo_deck:
                            _best_deck = evo_builder.best_deck()
                        elif cfg.pin_deck:
                            _best_deck = _fixed_deck
                        else:
                            _best_deck, _ = select_deck(
                                deck_builder, cfg.agent_school, cfg.device, greedy=True,
                                school_bias=cfg.school_bias,
                                cross_school_bias=cfg.cross_school_bias,
            damage_card_bias=cfg.damage_card_bias,
                                cross_school_pip_threshold=cfg.cross_school_pip_threshold,
                                forced_cards=cfg.forced_deck_cards or None,
                            )
                        _best_ckpt = {
                            "iteration":      iteration,
                            "smoothed_wr":    round(best_smoothed_wr, 4),
                            "model":          model.state_dict(),
                            "optimizer":      optimizer.state_dict(),
                            "deck_card_ids":  deck_to_card_ids(_best_deck),
                            "config": {
                                "agent_school": cfg.agent_school,
                                "agent_level":  cfg.agent_level,
                                "embed_dim":    cfg.embed_dim,
                                "n_heads":      cfg.n_heads,
                                "n_layers":     cfg.n_layers,
                            },
                        }
                        if cfg.use_evo_deck:
                            _best_ckpt["evo_state"] = evo_builder.state_dict()
                        else:
                            _best_ckpt["deck_builder"]   = deck_builder.state_dict()
                            _best_ckpt["deck_optimizer"]  = deck_optimizer.state_dict()
                        torch.save(_best_ckpt, best_path)
                        print(f"  → new best (smoothed WR {best_smoothed_wr:.3f}) saved to {best_path}")
                    else:
                        iters_no_improvement += 1
                        if iters_no_improvement >= cfg.patience:
                            print(
                                f"  → early stopping at iter {iteration}: "
                                f"no improvement for {cfg.patience} iters "
                                f"(best smoothed WR {best_smoothed_wr:.3f})"
                            )
                            break

        if iteration % cfg.save_every == 0:
            os.makedirs(f"rl/checkpoints/{cfg.agent_school}", exist_ok=True)
            path = f"rl/checkpoints/{cfg.agent_school}/model_{iteration:05d}.pt"
            latest_path = f"rl/checkpoints/{cfg.agent_school}/latest.pt"
            if cfg.use_evo_deck:
                greedy_deck = evo_builder.best_deck()
            elif cfg.pin_deck:
                greedy_deck = _fixed_deck
            else:
                greedy_deck, _ = select_deck(
                    deck_builder, cfg.agent_school, cfg.device, greedy=True,
                    school_bias=cfg.school_bias,
                    cross_school_bias=cfg.cross_school_bias,
            damage_card_bias=cfg.damage_card_bias,
                    cross_school_pip_threshold=cfg.cross_school_pip_threshold,
                    forced_cards=cfg.forced_deck_cards or None,
                )
            ckpt = {
                "iteration":      iteration,
                "model":          model.state_dict(),
                "optimizer":      optimizer.state_dict(),
                "deck_card_ids":  deck_to_card_ids(greedy_deck),
                "config": {
                    "agent_school": cfg.agent_school,
                    "agent_level":  cfg.agent_level,
                    "embed_dim":    cfg.embed_dim,
                    "n_heads":      cfg.n_heads,
                    "n_layers":     cfg.n_layers,
                },
            }
            if cfg.use_evo_deck:
                ckpt["evo_state"] = evo_builder.state_dict()
            else:
                ckpt["deck_builder"]       = deck_builder.state_dict()
                ckpt["deck_optimizer"]     = deck_optimizer.state_dict()
                ckpt["config"].update({
                    "deck_builder_embed_dim": cfg.deck_builder_embed_dim,
                    "deck_builder_n_heads":   cfg.deck_builder_n_heads,
                    "deck_builder_n_layers":  cfg.deck_builder_n_layers,
                })
            torch.save(ckpt, path)
            torch.save(ckpt, latest_path)
            print(f"  → saved {path}")

            # Save top-5 best decks (evo only)
            if cfg.use_evo_deck:
                best_dir = f"rl/checkpoints/{cfg.agent_school}/best_decks"
                os.makedirs(best_dir, exist_ok=True)
                top_decks = evo_builder.top_n_decks(n=5)
                for rank, entry in enumerate(top_decks, 1):
                    torch.save(
                        {
                            "deck_card_ids": deck_to_card_ids(entry["deck"]),
                            "win_rate":      round(entry["win_rate"], 4),
                            "wins":          entry["wins"],
                            "games":         entry["games"],
                            "iteration":     iteration,
                            "generation":    evo_builder.generation,
                        },
                        f"{best_dir}/deck_{rank}.pt",
                    )
                rates = "  ".join(f"#{r} {e['win_rate']:.2f}" for r, e in enumerate(top_decks, 1))
                print(f"  → best decks: {rates}")

    env.close()
    _log_f.close()
    return model


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--school", "-s", type=str, default="Fire",
                        help="Agent school to train (Fire, Ice, Storm, Life, Death, Myth, Balance)")
    parser.add_argument("--checkpoint", "-c", type=str, default=None,
                        help="Path to a .pt checkpoint to resume from")
    parser.add_argument("--reset-optimizers", "-r", action="store_true",
                        help="Load model weights only — discard Adam optimizer state")
    parser.add_argument("--reset-volume", action="store_true",
                        help="Delete all checkpoints for this school before training (fresh start)")
    parser.add_argument("--opponents", "-o", type=str, default=None,
                        help="Comma-separated trained opponent schools, e.g. Storm,Ice,Fire")
    parser.add_argument("--bc-coef", type=float, default=None,
                        help="Override bc_coef (e.g. 0.15 for round 2)")
    parser.add_argument("--log", "-l", type=str, default=None,
                        help="CSV log file path (default: rl/logs/{school}_{timestamp}.csv)")
    parser.add_argument("--iterations", type=int, default=None,
                        help="Number of training iterations (overrides Config.n_iterations)")
    parser.add_argument("--pin-deck", action="store_true",
                        help="Phase 1: fix deck to seed deck every game, skip deck builder")
    parser.add_argument("--phase1-wr-threshold", type=float, default=None,
                        help="Smoothed WR needed to advance each curriculum sub-phase")
    parser.add_argument("--phase2-wr-threshold", type=float, default=None,
                        help="Smoothed WR needed to enter phase 2 (evo deck, level 100)")
    parser.add_argument("--n-curriculum-phases", type=int, default=None,
                        help="Number of sub-phases in phase 1 (enemy level ramps up each phase)")
    args = parser.parse_args()

    if args.reset_volume:
        import shutil
        ckpt_dir = f"rl/checkpoints/{args.school}"
        if os.path.exists(ckpt_dir):
            shutil.rmtree(ckpt_dir)
            print(f"  → reset: deleted {ckpt_dir}")

    overrides = dict(
        agent_school      = args.school,
        resume_checkpoint = args.checkpoint,
        reset_optimizers  = args.reset_optimizers,
        log_file          = args.log,
    )
    if args.opponents:
        overrides["opponent_schools"] = [s.strip() for s in args.opponents.split(",")]
    if args.bc_coef is not None:
        overrides["bc_coef"] = args.bc_coef
    if args.iterations is not None:
        overrides["n_iterations"] = args.iterations
    if args.pin_deck:
        overrides["pin_deck"] = True
    if args.phase1_wr_threshold is not None:
        overrides["phase1_wr_threshold"] = args.phase1_wr_threshold
    if args.phase2_wr_threshold is not None:
        overrides["phase2_wr_threshold"] = args.phase2_wr_threshold
    if args.n_curriculum_phases is not None:
        overrides["n_curriculum_phases"] = args.n_curriculum_phases

    train(Config(**overrides))
