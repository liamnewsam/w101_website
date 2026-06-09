"""Inference utilities for deploying trained W101 models as bots in live games.

Key public API:
    list_checkpoints()             → list of checkpoint metadata dicts
    load_model(path, device)       → (model, config_dict)
    take_model_action(model, game, player, device, max_retries)
"""

from __future__ import annotations

import os
import glob
from pathlib import Path

import numpy as np
import torch

from rl.model import TransformerActorCritic
from rl.env import (
    CARD_DIM, PLAYER_DIM, GAME_DIM,
    EFFECT_TOKEN_DIM, MAX_EFFECT_TOKENS,
    HAND_SIZE, MAX_PLAYERS, MAX_TEAM_SIZE, MAX_TOTAL_CARDS,
    N_TARGET_SLOTS, N_PIP_SCHOOL_ACTIONS, N_ACTIONS,
    CAST_BASE, DISCARD_BASE, PIP_SCHOOL_BASE,
    SCHOOLS, SCHOOL_TO_IDX,
    CARD_TYPES, CARD_TYPE_TO_IDX,
    PIP_KEYS,
    _encode_all_cards,
    _encode_hanging_effect_tokens,
)

_CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"


# ──────────────────────────────────────────────────────────────────────────────
# Checkpoint discovery
# ──────────────────────────────────────────────────────────────────────────────

def get_school_best_deck(school: str) -> list[str]:
    """Return the deck_card_ids from rl/checkpoints/<School>/best.pt."""
    path = _CHECKPOINT_DIR / school / "best.pt"
    ckpt = torch.load(str(path), map_location="cpu", weights_only=False)
    return ckpt.get("deck_card_ids", [])


def pick_demo_ai_deck(school: str) -> tuple[list[str], str]:
    """Randomly choose the AI deck for a demo game.

    1/6 chance each: best.pt deck or one of the 5 best_decks/*.pt decks.
    Returns (deck_card_ids, source_label).
    """
    best_path = _CHECKPOINT_DIR / school / "best.pt"
    best_decks_dir = _CHECKPOINT_DIR / school / "best_decks"
    best_deck_paths = sorted(glob.glob(str(best_decks_dir / "deck_*.pt")))

    options = [str(best_path)] + best_deck_paths
    chosen = options[os.urandom(1)[0] % len(options)] if options else str(best_path)

    ckpt = torch.load(chosen, map_location="cpu", weights_only=False)
    card_ids = ckpt.get("deck_card_ids", [])
    return card_ids, chosen


def list_checkpoints() -> list[dict]:
    """Return metadata for every checkpoint in rl/checkpoints/, newest first."""
    paths = sorted(glob.glob(str(_CHECKPOINT_DIR / "model_*.pt")), reverse=True)
    results = []
    for path in paths:
        try:
            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            cfg = ckpt.get("config", {})
            results.append({
                "path": path,
                "filename": os.path.basename(path),
                "iteration": ckpt.get("iteration", 0),
                "agent_school": cfg.get("agent_school", "Unknown"),
                "agent_level": cfg.get("agent_level", 1),
                "agent_deck_name": cfg.get("agent_deck_name"),
                "embed_dim": cfg.get("embed_dim", 64),
                "n_heads": cfg.get("n_heads", 4),
                "n_layers": cfg.get("n_layers", 2),
            })
        except Exception as e:
            results.append({"path": path, "filename": os.path.basename(path), "error": str(e)})
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Model loading
# ──────────────────────────────────────────────────────────────────────────────

def load_model(checkpoint_path: str, device: str = "cpu") -> tuple:
    """Load a TransformerActorCritic from a checkpoint.

    Returns:
        (model, config_dict)  where config_dict contains agent_school, agent_level, etc.
    """
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    cfg = ckpt.get("config", {})

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
        embed_dim            = cfg.get("embed_dim", 64),
        n_heads              = cfg.get("n_heads", 4),
        n_layers             = cfg.get("n_layers", 2),
    ).to(device)

    model.load_state_dict(ckpt["model"])
    model.eval()
    # Propagate the saved deck (if any) through the config dict so callers
    # don't need to know the checkpoint key name.
    cfg["deck_card_ids"] = ckpt.get("deck_card_ids", None)
    return model, cfg


# ──────────────────────────────────────────────────────────────────────────────
# Observation helpers
# ──────────────────────────────────────────────────────────────────────────────



def _encode_one_player(p) -> np.ndarray:
    feats = [p.maxHealth, p.health / float(p.maxHealth)]
    for k in PIP_KEYS:
        feats.append(p.pips.get(k, 0) * 1.0)
    one_hot = [0.0] * len(SCHOOLS)
    one_hot[SCHOOL_TO_IDX.get(p.school, 0)] = 1.0
    feats.extend(one_hot)
    return np.array(feats, dtype=np.float32)


def _encode_players(game, player, my_team, enemy_team) -> np.ndarray:
    arr = np.zeros((MAX_PLAYERS, PLAYER_DIM), dtype=np.float32)
    for p_idx, p in enumerate(my_team[:MAX_TEAM_SIZE]):
        arr[p_idx] = _encode_one_player(p)
    for p_idx, p in enumerate(enemy_team[:MAX_TEAM_SIZE]):
        arr[MAX_TEAM_SIZE + p_idx] = _encode_one_player(p)
    return arr


def _global_idx_for_player(target, my_team, enemy_team) -> int:
    """Slot index from the perspective of `player`: my_team = slots 0.., enemy_team = MAX_TEAM_SIZE+.."""
    for i, p in enumerate(my_team[:MAX_TEAM_SIZE]):
        if p.user_id == target.user_id:
            return i
    for i, p in enumerate(enemy_team[:MAX_TEAM_SIZE]):
        if p.user_id == target.user_id:
            return MAX_TEAM_SIZE + i
    return -1


def _action_mask(game, player, my_team, enemy_team) -> np.ndarray:
    mask = np.zeros(N_ACTIONS, dtype=np.float32)
    mask[0] = 1.0  # pass always legal

    play = game.playability.get(player.user_id, [])
    for card_i, info in enumerate(play[:HAND_SIZE]):
        if not info["playable"]:
            continue
        targets = info["targets"]
        base = CAST_BASE + card_i * N_TARGET_SLOTS
        if not targets:
            mask[base + MAX_PLAYERS] = 1.0
        else:
            for t in targets:
                j = _global_idx_for_player(t, my_team, enemy_team)
                if j >= 0:
                    mask[base + j] = 1.0

    for i in range(min(HAND_SIZE, len(player.deck.play_hand))):
        mask[DISCARD_BASE + i] = 1.0

    for j in range(N_PIP_SCHOOL_ACTIONS):
        mask[PIP_SCHOOL_BASE + j] = 1.0

    return mask


def _encode_game_token(game, player, max_turns: int) -> np.ndarray:
    vec = np.zeros(GAME_DIM, dtype=np.float32)
    vec[0] = min(game.turns / float(max_turns), 1.0)
    vec[1] = len(player.deck.play_hand) / float(HAND_SIZE)
    sel = player.school_pip_select
    if sel in SCHOOL_TO_IDX:
        vec[2 + SCHOOL_TO_IDX[sel]] = 1.0
    return vec


def obs_for_player(game, player, max_turns: int = 300) -> dict:
    """Build a model-ready observation dict centered on `player`."""
    if player in game.teams[0]:
        my_team, enemy_team = game.teams[0], game.teams[1]
    else:
        my_team, enemy_team = game.teams[1], game.teams[0]

    play = game.playability.get(player.user_id, [])
    return {
        "cards":       _encode_all_cards(player, play),
        "players":     _encode_players(game, player, my_team, enemy_team),
        "effects":     _encode_hanging_effect_tokens(game.teams),
        "game":        _encode_game_token(game, player, max_turns),
        "action_mask": _action_mask(game, player, my_team, enemy_team),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Action application
# ──────────────────────────────────────────────────────────────────────────────

def _apply_action(action_int: int, game, player, my_team, enemy_team) -> bool:
    """Apply action_int for player.  Returns True if it was a terminal action (pass/cast)."""
    if action_int == 0:
        game.player_pass(player)
        return True

    if action_int >= PIP_SCHOOL_BASE:
        school = SCHOOLS[action_int - PIP_SCHOOL_BASE]
        player.school_pip_select = school
        game.log.append({"type": "action", "player": player.user_id, "action": "pip_school_change", "school": school})
        return False

    if action_int >= DISCARD_BASE:
        card_idx = action_int - DISCARD_BASE
        hand = player.deck.play_hand
        if card_idx < len(hand):
            game.player_discard(player, hand[card_idx].instance_id)
        return False

    encoded     = action_int - CAST_BASE
    card_idx    = encoded // N_TARGET_SLOTS
    target_slot = encoded %  N_TARGET_SLOTS

    if target_slot == MAX_PLAYERS:
        target_id = None
    else:
        team_idx   = target_slot // MAX_TEAM_SIZE
        player_idx = target_slot %  MAX_TEAM_SIZE
        team = my_team if team_idx == 0 else enemy_team
        if player_idx >= len(team):
            game.player_pass(player)
            return True
        target_id = team[player_idx].user_id

    play = game.playability.get(player.user_id, [])
    if card_idx < len(play) and play[card_idx]["playable"]:
        if game.player_cast(player, card_idx, target_id):
            return True

    game.player_pass(player)
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point for game integration
# ──────────────────────────────────────────────────────────────────────────────

def take_model_action(
    model: TransformerActorCritic,
    game,
    player,
    device: str = "cpu",
    max_turns: int = 300,
    max_retries: int = 8,
) -> None:
    """Drive `player`'s turn using the trained model.

    Handles non-terminal actions (discard, pip-select) by re-querying the model
    up to max_retries times before falling back to pass.
    """
    if player in game.teams[0]:
        my_team, enemy_team = game.teams[0], game.teams[1]
    else:
        my_team, enemy_team = game.teams[1], game.teams[0]

    for _ in range(max_retries):
        obs = obs_for_player(game, player, max_turns)

        cards_t   = torch.as_tensor(obs["cards"][None],        device=device)
        players_t = torch.as_tensor(obs["players"][None],      device=device)
        effects_t = torch.as_tensor(obs["effects"][None],      device=device)
        game_t    = torch.as_tensor(obs["game"][None],         device=device)
        mask_t    = torch.as_tensor(obs["action_mask"][None],  device=device)

        with torch.no_grad():
            action, _, _ = model.act(cards_t, players_t, effects_t, game_t, mask_t)

        action_int = int(action.item())
        terminal = _apply_action(action_int, game, player, my_team, enemy_team)
        if terminal:
            return

    # Fallback: force a pass so the turn can always resolve
    game.player_pass(player)
