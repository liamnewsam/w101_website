"""Deck-building agent trained jointly with the game-playing agent (end-to-end PPO).

The deck builder autoregressively picks DECK_SIZE cards from the school's card pool
one at a time.  After the resulting game finishes, the win/loss outcome is assigned
as a terminal reward to all selection steps, and both agents are updated with PPO.
"""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical

import json
from pathlib import Path

from Card import CARDS_BY_SCHOOL
from Deck import Deck, Card as GameCard

from rl.env import (SCHOOLS, SCHOOL_TO_IDX, CARD_TYPES, CARD_TYPE_TO_IDX,
                    _encode_card_effects, MAXIMUM_CARD_EFFECTS, CARD_EFFECT_SIZE)

_MISC_IDS: frozenset[str] = frozenset(
    c["id"]
    for c in json.loads(
        (Path(__file__).parent.parent / "static/w101/spells/spell_data/misc.json").read_text()
    )
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MAX_POOL_SIZE = 300  # covers all 297 cards across all 7 schools
DECK_SIZE     = 30   # cards selected per deck  (matches MAX_TOTAL_CARDS)
MAX_COPIES    = 4    # max copies of any single card

# Pool card obs: school(7) + pip_norm(1) + type(12) + effects(MAXIMUM_CARD_EFFECTS*CARD_EFFECT_SIZE)
POOL_CARD_DIM = len(SCHOOLS) + 1 + len(CARD_TYPES) + MAXIMUM_CARD_EFFECTS * CARD_EFFECT_SIZE
# + count_norm(1) + is_agent_school(1)
POOL_OBS_DIM  = POOL_CARD_DIM + 2                          # 32


# ─────────────────────────────────────────────────────────────────────────────
# Card pool helpers
# ─────────────────────────────────────────────────────────────────────────────

def _encode_pool_card(cd) -> np.ndarray:
    vec = np.zeros(POOL_CARD_DIM, dtype=np.float32)
    col = 0
    vec[col + SCHOOL_TO_IDX.get(cd.school, 0)] = 1.0
    col += len(SCHOOLS)
    pip_val = cd.pips if isinstance(cd.pips, (int, float)) else 3
    vec[col] = min(float(pip_val) / 7.0, 1.0)
    col += 1
    type_idx = CARD_TYPE_TO_IDX.get(cd.type, CARD_TYPE_TO_IDX["other"])
    vec[col + type_idx] = 1.0
    col += len(CARD_TYPES)
    vec[col : col + MAXIMUM_CARD_EFFECTS * CARD_EFFECT_SIZE] = _encode_card_effects(cd.effects)
    return vec


# Single global pool of all cards across every school — pre-computed once.
_ALL_POOL_CACHE: tuple[list, np.ndarray] | None = None

def _get_all_pool() -> tuple[list, np.ndarray]:
    """Return (all_card_defs, base_enc) where base_enc is (MAX_POOL_SIZE, POOL_CARD_DIM)."""
    global _ALL_POOL_CACHE
    if _ALL_POOL_CACHE is None:
        all_cards: list = []
        for school in SCHOOLS:
            all_cards.extend(
                c for c in CARDS_BY_SCHOOL.get(school.lower(), [])
                if c.id not in _MISC_IDS
            )
        base = np.zeros((MAX_POOL_SIZE, POOL_CARD_DIM), dtype=np.float32)
        for i, cd in enumerate(all_cards[:MAX_POOL_SIZE]):
            base[i] = _encode_pool_card(cd)
        _ALL_POOL_CACHE = (all_cards, base)
    return _ALL_POOL_CACHE


_SCHOOL_MASK_CACHE: dict[str, np.ndarray] = {}

def _get_school_mask(school: str) -> np.ndarray:
    """Return a (MAX_POOL_SIZE,) float32 array with 1.0 at in-school card positions."""
    key = school.lower()
    if key not in _SCHOOL_MASK_CACHE:
        all_cards, _ = _get_all_pool()
        mask = np.zeros(MAX_POOL_SIZE, dtype=np.float32)
        for i, cd in enumerate(all_cards[:MAX_POOL_SIZE]):
            if cd.school.lower() == key:
                mask[i] = 1.0
        _SCHOOL_MASK_CACHE[key] = mask
    return _SCHOOL_MASK_CACHE[key]


def encode_pool_obs(school: str, counts: np.ndarray) -> np.ndarray:
    """Build (MAX_POOL_SIZE, POOL_OBS_DIM) obs: base features + count_norm + is_agent_school."""
    _, base    = _get_all_pool()
    count_col  = (counts / float(MAX_COPIES)).reshape(-1, 1)   # (MAX_POOL_SIZE, 1)
    school_col = _get_school_mask(school).reshape(-1, 1)        # (MAX_POOL_SIZE, 1)
    return np.concatenate([base, count_col, school_col], axis=1) # (MAX_POOL_SIZE, POOL_OBS_DIM)


def build_deck(selections: list[int]) -> Deck:
    """Build a Deck from a list of global pool indices (duplicates allowed)."""
    all_cards, _ = _get_all_pool()
    cards = [GameCard(all_cards[idx]) for idx in selections]
    return Deck("AgentBuiltDeck", cards)


# ─────────────────────────────────────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────────────────────────────────────

class DeckBuilderNet(nn.Module):
    """Small transformer that scores pool cards at each autoregressive selection step.

    Input:  pool_obs (B, MAX_POOL_SIZE, POOL_OBS_DIM) — card features + current count_norm
            mask     (B, MAX_POOL_SIZE)               — 1 where card is still selectable
    Output: logits (B, MAX_POOL_SIZE), value (B,)
    """

    def __init__(
        self,
        pool_obs_dim: int = POOL_OBS_DIM,
        pool_size:    int = MAX_POOL_SIZE,
        embed_dim:    int = 32,
        n_heads:      int = 2,
        n_layers:     int = 2,
    ):
        super().__init__()
        self.pool_size = pool_size

        card_hidden = max(embed_dim * 2, pool_obs_dim // 4)
        self.card_encoder = nn.Sequential(
            nn.Linear(pool_obs_dim, card_hidden),
            nn.LayerNorm(card_hidden),
            nn.GELU(),
            nn.Linear(card_hidden, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
        )
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        nn.init.trunc_normal_(self.cls_token, std=0.02)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=n_heads,
            dim_feedforward=embed_dim * 4,
            dropout=0.0,
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        self.score_head = nn.Linear(embed_dim, 1)
        self.value_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, 1),
        )

        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=0.01)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, pool_obs: torch.Tensor, mask: torch.Tensor):
        B = pool_obs.shape[0]
        card_tokens = self.card_encoder(pool_obs)           # (B, POOL_SIZE, E)
        cls = self.cls_token.expand(B, -1, -1)              # (B, 1, E)
        tokens = torch.cat([cls, card_tokens], dim=1)       # (B, 1+POOL_SIZE, E)
        out = self.transformer(tokens)                      # (B, 1+POOL_SIZE, E)

        cls_out  = out[:, 0]                                # (B, E)
        card_out = out[:, 1:]                               # (B, POOL_SIZE, E)

        logits = self.score_head(card_out).squeeze(-1)      # (B, POOL_SIZE)
        logits = logits.masked_fill(mask < 0.5, float("-inf"))
        value  = self.value_head(cls_out).squeeze(-1)       # (B,)
        return logits, value

    @torch.no_grad()
    def act(self, pool_obs: torch.Tensor, mask: torch.Tensor):
        logits, value = self(pool_obs, mask)
        dist   = Categorical(logits=logits)
        action = dist.sample()
        return action, dist.log_prob(action), value

    def evaluate(self, pool_obs: torch.Tensor, mask: torch.Tensor, action: torch.Tensor,
                 school_bias_vec: "torch.Tensor | None" = None):
        logits, value = self(pool_obs, mask)
        if school_bias_vec is not None:
            logits = logits + school_bias_vec.unsqueeze(0)
            logits = logits.masked_fill(mask < 0.5, float("-inf"))
        dist = Categorical(logits=logits)
        return dist.log_prob(action), value, dist.entropy()


# ─────────────────────────────────────────────────────────────────────────────
# Rollout Buffer
# ─────────────────────────────────────────────────────────────────────────────

class DeckBuilderBuffer:
    """Stores complete deck-selection episodes (each DECK_SIZE steps).

    The game terminal reward (+1 win / -1 loss / 0 draw) is placed on the final
    selection step; all intermediate steps get reward 0.  GAE propagates it back.
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        self._ptr     = 0
        n = capacity * DECK_SIZE
        self.pool_obs  = np.zeros((n, MAX_POOL_SIZE, POOL_OBS_DIM), dtype=np.float32)
        self.masks     = np.zeros((n, MAX_POOL_SIZE),               dtype=np.float32)
        self.actions   = np.zeros(n,                                dtype=np.int64)
        self.log_probs = np.zeros(n,                                dtype=np.float32)
        self.rewards   = np.zeros(n,                                dtype=np.float32)
        self.values    = np.zeros(n,                                dtype=np.float32)
        self.dones     = np.zeros(n,                                dtype=np.float32)

    @property
    def full(self) -> bool:
        return self._ptr >= self.capacity

    def push_episode(
        self,
        pool_obs:    np.ndarray,  # (DECK_SIZE, MAX_POOL_SIZE, POOL_OBS_DIM)
        masks:       np.ndarray,  # (DECK_SIZE, MAX_POOL_SIZE)
        actions:     np.ndarray,  # (DECK_SIZE,)
        log_probs:   np.ndarray,  # (DECK_SIZE,)
        values:      np.ndarray,  # (DECK_SIZE,)
        game_reward: float,
    ):
        s = self._ptr * DECK_SIZE
        e = s + DECK_SIZE
        self.pool_obs[s:e]  = pool_obs
        self.masks[s:e]     = masks
        self.actions[s:e]   = actions
        self.log_probs[s:e] = log_probs
        self.values[s:e]    = values
        self.rewards[s:e]   = 0.0
        self.rewards[e - 1] = game_reward
        self.dones[s:e]     = 0.0
        self.dones[e - 1]   = 1.0
        self._ptr += 1

    def compute_gae(self, gamma: float, lam: float):
        n   = self._ptr * DECK_SIZE
        adv = np.zeros(n, dtype=np.float32)
        gae = 0.0
        for t in reversed(range(n)):
            next_val = 0.0 if self.dones[t] else self.values[t + 1]
            non_term = 1.0 - self.dones[t]
            delta    = self.rewards[t] + gamma * next_val * non_term - self.values[t]
            gae      = delta + gamma * lam * non_term * gae
            adv[t]   = gae
        return adv, adv + self.values[:n]

    def tensors(self, device):
        n = self._ptr * DECK_SIZE
        return (
            torch.as_tensor(self.pool_obs[:n],  device=device),
            torch.as_tensor(self.masks[:n],     device=device),
            torch.as_tensor(self.actions[:n],   device=device),
            torch.as_tensor(self.log_probs[:n], device=device),
        )

    def clear(self):
        self._ptr = 0


# ─────────────────────────────────────────────────────────────────────────────
# Deck selection (called at the start of each game episode)
# ─────────────────────────────────────────────────────────────────────────────

def deck_to_card_ids(deck: Deck) -> list[str]:
    """Serialise a Deck as a list of card-definition IDs."""
    return [card.card_def.id for card in deck.cards]


def deck_from_card_ids(card_ids: list[str]) -> Deck:
    """Reconstruct a Deck from a saved list of card-definition IDs."""
    from Card import CARD_BY_ID
    cards = [GameCard(CARD_BY_ID[cid]) for cid in card_ids if cid in CARD_BY_ID]
    return Deck("AgentBuiltDeck", cards)


def deck_to_pool_indices(deck: Deck) -> list[int]:
    """Map each card in a Deck to its index in the global pool (for BC loss)."""
    all_cards, _ = _get_all_pool()
    id_to_idx = {cd.id: i for i, cd in enumerate(all_cards[:MAX_POOL_SIZE])}
    return [id_to_idx[card.card_def.id] for card in deck.cards if card.card_def.id in id_to_idx]


_DAMAGE_TYPES = {"damage", "DoT", "drain"}

def make_school_bias_vec(
    school: str,
    bias: float,
    cross_school_bias: float = 0.0,
    cross_school_pip_threshold: int = 3,
    damage_card_bias: float = 0.0,
    device: str = "cpu",
) -> torch.Tensor:
    """Return a (MAX_POOL_SIZE,) stratified logit-bias tensor.

    - In-school cards              → bias  (+damage_card_bias if damage/DoT/drain type)
    - Off-school cards with pip cost <= cross_school_pip_threshold → cross_school_bias
    - Everything else              → 0
    """
    all_cards, _ = _get_all_pool()
    vec = np.zeros(MAX_POOL_SIZE, dtype=np.float32)
    school_lower = school.lower()
    for i, cd in enumerate(all_cards[:MAX_POOL_SIZE]):
        if cd.school.lower() == school_lower:
            vec[i] = bias
            if damage_card_bias > 0 and cd.type in _DAMAGE_TYPES:
                vec[i] += damage_card_bias
        elif cross_school_bias > 0:
            pips = cd.pips
            if isinstance(pips, (int, float)):
                pip_cost = float(pips)
            elif isinstance(pips, dict):
                pip_cost = float(pips.get("regular", 0))
            else:  # "X"
                pip_cost = float("inf")
            if pip_cost <= cross_school_pip_threshold:
                vec[i] = cross_school_bias
    return torch.as_tensor(vec, device=device)


def select_deck(
    model:                      DeckBuilderNet,
    school:                     str,
    device:                     str       = "cpu",
    greedy:                     bool      = False,
    school_bias:                float     = 5.0,
    cross_school_bias:          float     = 0.0,
    cross_school_pip_threshold: int       = 3,
    damage_card_bias:           float     = 0.0,
    forced_cards:               list[str] = None,
) -> tuple[Deck, dict]:
    """Autoregressively select DECK_SIZE cards from the global pool for the given school.

    forced_cards: optional list of card-definition IDs to pre-seed into the deck
    before autoregressive selection begins (e.g. ["reshuffle"]).

    Returns:
        deck:       Deck object ready to pass to the environment
        trajectory: dict of (DECK_SIZE, ...) arrays for DeckBuilderBuffer.push_episode
    """
    all_cards, _ = _get_all_pool()
    real_n    = min(len(all_cards), MAX_POOL_SIZE)
    counts    = np.zeros(MAX_POOL_SIZE, dtype=np.float32)
    bias_vec  = make_school_bias_vec(school, school_bias, cross_school_bias, cross_school_pip_threshold, damage_card_bias, device)
    selections: list[int] = []

    # Build ordered list of forced card indices (processed first in the loop)
    forced_indices: list[int] = []
    if forced_cards:
        id_to_idx = {cd.id: i for i, cd in enumerate(all_cards[:real_n])}
        for cid in forced_cards:
            idx = id_to_idx.get(cid)
            if idx is not None and counts[idx] < MAX_COPIES:
                forced_indices.append(idx)

    t_pool_obs  = np.zeros((DECK_SIZE, MAX_POOL_SIZE, POOL_OBS_DIM), dtype=np.float32)
    t_masks     = np.zeros((DECK_SIZE, MAX_POOL_SIZE),               dtype=np.float32)
    t_actions   = np.zeros(DECK_SIZE,                                dtype=np.int64)
    t_log_probs = np.zeros(DECK_SIZE,                                dtype=np.float32)
    t_values    = np.zeros(DECK_SIZE,                                dtype=np.float32)

    model.eval()
    for step in range(DECK_SIZE):
        obs    = encode_pool_obs(school, counts)
        mask   = (counts < MAX_COPIES).astype(np.float32)
        mask[real_n:] = 0.0

        obs_t  = torch.as_tensor(obs[None],  device=device)

        if step < len(forced_indices):
            # Force this card: build a single-entry mask so the model must pick it
            forced_idx = forced_indices[step]
            forced_mask = np.zeros(MAX_POOL_SIZE, dtype=np.float32)
            forced_mask[forced_idx] = 1.0
            mask_t = torch.as_tensor(forced_mask[None], device=device)
        else:
            mask_t = torch.as_tensor(mask[None], device=device)

        with torch.no_grad():
            logits, value = model(obs_t, mask_t)
            logits = logits + bias_vec.unsqueeze(0)
            logits = logits.masked_fill(mask_t < 0.5, float("-inf"))
            if greedy:
                action   = logits.argmax(dim=-1)
                log_prob = torch.zeros(1, device=device)
            else:
                dist     = Categorical(logits=logits)
                action   = dist.sample()
                log_prob = dist.log_prob(action)

        idx = int(action.item())
        counts[idx] += 1
        selections.append(idx)

        t_pool_obs[step]  = obs
        t_masks[step]     = mask   # store the real mask for PPO, not the forced one
        t_actions[step]   = idx
        t_log_probs[step] = float(log_prob.item())
        t_values[step]    = float(value.item())

    return build_deck(selections), {
        "pool_obs":  t_pool_obs,
        "masks":     t_masks,
        "actions":   t_actions,
        "log_probs": t_log_probs,
        "values":    t_values,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Behavioural cloning loss
# ─────────────────────────────────────────────────────────────────────────────

def compute_bc_loss(
    model:           DeckBuilderNet,
    bc_indices:      list,               # len-30 list of pool indices (target deck)
    school:          str,
    school_bias_vec: "torch.Tensor | None",
    device:          str,
) -> torch.Tensor:
    """Mean cross-entropy of model's distribution against the target deck, step by step."""
    all_cards, _ = _get_all_pool()
    real_n  = min(len(all_cards), MAX_POOL_SIZE)
    counts  = np.zeros(MAX_POOL_SIZE, dtype=np.float32)
    total   = torch.tensor(0.0, device=device)

    for target_idx in bc_indices:
        obs    = encode_pool_obs(school, counts)
        mask   = (counts < MAX_COPIES).astype(np.float32)
        mask[real_n:] = 0.0

        obs_t  = torch.as_tensor(obs[None],  device=device)
        mask_t = torch.as_tensor(mask[None], device=device)

        logits, _ = model(obs_t, mask_t)                      # (1, MAX_POOL_SIZE)
        if school_bias_vec is not None:
            logits = logits + school_bias_vec.unsqueeze(0)
            logits = logits.masked_fill(mask_t < 0.5, float("-inf"))

        log_probs = F.log_softmax(logits[0], dim=-1)          # (MAX_POOL_SIZE,)
        total     = total - log_probs[target_idx]
        counts[target_idx] += 1

    return total / len(bc_indices)


# ─────────────────────────────────────────────────────────────────────────────
# PPO update
# ─────────────────────────────────────────────────────────────────────────────

def ppo_update_deck_builder(
    model:            DeckBuilderNet,
    optimizer:        torch.optim.Optimizer,
    buffer:           DeckBuilderBuffer,
    cfg,
    school_bias_vec:  "torch.Tensor | None" = None,
    bc_deck_indices:  "list | None"         = None,
    run_ppo:          bool                  = True,
) -> dict:
    pg_losses, vf_losses, ent_losses, bc_losses = [], [], [], []
    model.train()

    if run_ppo:
        adv, returns = buffer.compute_gae(cfg.gamma, cfg.lam)
        adv_t = torch.as_tensor(adv,     device=cfg.device)
        ret_t = torch.as_tensor(returns, device=cfg.device)
        adv_t = (adv_t - adv_t.mean()) / (adv_t.std() + 1e-8)

        pool_obs, masks, actions, old_log_probs = buffer.tensors(cfg.device)
        n = len(actions)

        for _ in range(cfg.n_epochs):
            idxs = torch.randperm(n, device=cfg.device)
            for start in range(0, n, cfg.batch_size):
                b = idxs[start : start + cfg.batch_size]

                log_probs, values, entropy = model.evaluate(pool_obs[b], masks[b], actions[b], school_bias_vec)
                ratio  = torch.exp(log_probs - old_log_probs[b])
                adv_b  = adv_t[b]

                pg_loss  = -torch.min(
                    ratio * adv_b,
                    ratio.clamp(1 - cfg.clip_eps, 1 + cfg.clip_eps) * adv_b,
                ).mean()
                vf_loss  = F.mse_loss(values, ret_t[b])
                ent_loss = -entropy.mean()
                db_ent_coef = getattr(cfg, "deck_builder_ent_coef", cfg.ent_coef)
                loss     = pg_loss + cfg.vf_coef * vf_loss + db_ent_coef * ent_loss

                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.max_grad_norm)
                optimizer.step()

                pg_losses.append(pg_loss.item())
                vf_losses.append(vf_loss.item())
                ent_losses.append(-ent_loss.item())

    # BC step: always runs (once per epoch, or once if PPO was skipped)
    n_bc_steps = cfg.n_epochs if run_ppo else 1
    if bc_deck_indices and cfg.bc_coef > 0.0:
        for _ in range(n_bc_steps):
            bc_loss = compute_bc_loss(
                model, bc_deck_indices, cfg.agent_school, school_bias_vec, cfg.device
            )
            optimizer.zero_grad()
            (cfg.bc_coef * bc_loss).backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.max_grad_norm)
            optimizer.step()
            bc_losses.append(bc_loss.item())

    return {
        "db_pg":  float(np.mean(pg_losses)) if pg_losses else 0.0,
        "db_vf":  float(np.mean(vf_losses)) if vf_losses else 0.0,
        "db_ent": float(np.mean(ent_losses)) if ent_losses else 0.0,
        "db_bc":  float(np.mean(bc_losses)) if bc_losses else 0.0,
    }
