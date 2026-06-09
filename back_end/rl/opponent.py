"""Trained-agent opponent wrapper for multi-agent self-play.

Usage in train.py:
    from rl.opponent import TrainedOpponent, load_opponent
    opp = load_opponent("rl/checkpoints/Ice/latest.pt", cfg.device, cfg.max_turns)
    env = W101Env(..., opponent_policies=[opp])
"""
from __future__ import annotations

import os
import torch
import numpy as np

from rl.env import (
    W101Env,
    SCHOOLS, SCHOOL_TO_IDX, HAND_SIZE, MAX_PLAYERS, MAX_TEAM_SIZE, PLAYER_DIM, GAME_DIM,
    N_ACTIONS, N_TARGET_SLOTS, CAST_BASE, DISCARD_BASE, PIP_SCHOOL_BASE,
    _encode_all_cards, _encode_hanging_effect_tokens,
)


def _build_obs_for(game, player, own_team_idx: int, max_turns: int, pip_change_turn: int) -> dict:
    """Build an observation dict from `player`'s perspective.

    `own_team_idx` is the index of the player's team in game.teams (0 or 1).
    Teams are flipped so the player's own team always appears at position 0,
    matching the encoding the model was trained on.
    """
    if own_team_idx == 0:
        teams_view = game.teams
    else:
        teams_view = [game.teams[1], game.teams[0]]

    play = game.playability.get(player.user_id, [])

    # Cards (player's own deck/hand)
    cards = _encode_all_cards(player, play)

    # Players (flipped team order)
    arr = np.zeros((MAX_PLAYERS, PLAYER_DIM), dtype=np.float32)
    for t_idx, team in enumerate(teams_view):
        for p_idx, p in enumerate(team[:MAX_TEAM_SIZE]):
            arr[t_idx * MAX_TEAM_SIZE + p_idx] = W101Env._encode_one_player(p)

    # Effects (flipped)
    effects = _encode_hanging_effect_tokens(teams_view)

    # Game scalar
    game_obs = np.zeros(GAME_DIM, dtype=np.float32)
    game_obs[0] = min(game.turns / float(max_turns), 1.0)
    game_obs[1] = len(player.deck.play_hand) / float(HAND_SIZE)
    sel = player.school_pip_select
    if sel in SCHOOL_TO_IDX:
        game_obs[2 + SCHOOL_TO_IDX[sel]] = 1.0

    # Action mask — pass and cast only (bots skip discard / pip-school)
    mask = np.zeros(N_ACTIONS, dtype=np.float32)
    mask[0] = 1.0  # pass always legal
    for card_i, info in enumerate(play[:HAND_SIZE]):
        if not info["playable"]:
            continue
        base = 1 + card_i * N_TARGET_SLOTS
        targets = info["targets"]
        if not targets:
            mask[base + MAX_PLAYERS] = 1.0  # AoE / self-cast
        else:
            for p in targets:
                for t_idx, team in enumerate(teams_view):
                    for p_idx, tp in enumerate(team):
                        if tp.user_id == p.user_id:
                            mask[base + t_idx * MAX_TEAM_SIZE + p_idx] = 1.0

    return {"cards": cards, "players": arr, "effects": effects,
            "game": game_obs, "action_mask": mask}


class TrainedOpponent:
    """Wraps a trained TransformerActorCritic as a game bot.

    At each reset, call `attach(game, enemy_player, own_team_idx)` to register
    the bot's action function on the game's model_agents dict.
    """

    def __init__(self, model, device: str, max_turns: int = 100):
        self.model     = model
        self.device    = device
        self.max_turns = max_turns
        model.eval()

    def attach(self, game, player, own_team_idx: int) -> None:
        """Register this opponent to act for `player` in `game`."""
        game.model_agents[player.user_id] = self._make_fn(game, player, own_team_idx)

    def _make_fn(self, game, player, own_team_idx: int):
        def act(player):
            obs = _build_obs_for(game, player, own_team_idx, self.max_turns, -1)

            with torch.no_grad():
                cards_t   = torch.as_tensor(obs["cards"][None],       device=self.device)
                players_t = torch.as_tensor(obs["players"][None],     device=self.device)
                effects_t = torch.as_tensor(obs["effects"][None],     device=self.device)
                game_t    = torch.as_tensor(obs["game"][None],        device=self.device)
                mask_t    = torch.as_tensor(obs["action_mask"][None], device=self.device)
                action, _, _ = self.model.act(cards_t, players_t, effects_t, game_t, mask_t)

            action_idx = int(action.item())

            # Pip-school: apply the change, then pass to end the turn
            if action_idx >= PIP_SCHOOL_BASE:
                school = SCHOOLS[action_idx - PIP_SCHOOL_BASE]
                player.school_pip_select = school
                game.log.append({"type": "action", "player": player.user_id,
                                  "action": "pip_school_change", "school": school})
                game.player_pass(player)
                return

            # Discard outputs → pass
            if action_idx >= DISCARD_BASE or action_idx == 0:
                game.player_pass(player)
                return

            encoded     = action_idx - CAST_BASE
            card_idx    = encoded // N_TARGET_SLOTS
            target_slot = encoded %  N_TARGET_SLOTS

            if target_slot == MAX_PLAYERS:
                target_id = None  # AoE
            else:
                t_idx  = target_slot // MAX_TEAM_SIZE
                p_idx  = target_slot %  MAX_TEAM_SIZE
                # Un-flip: in obs t_idx 0 = own team, 1 = opponents
                actual_t = (1 - t_idx) if own_team_idx == 1 else t_idx
                team = game.teams[actual_t]
                if p_idx >= len(team):
                    game.player_pass(player)
                    return
                target_id = team[p_idx].user_id

            play = game.playability.get(player.user_id, [])
            if card_idx < len(play) and play[card_idx]["playable"]:
                if game.player_cast(player, card_idx, target_id):
                    return

            game.player_pass(player)

        return act


def load_opponent(
    checkpoint_path: str,
    device: str,
    max_turns: int = 100,
) -> "tuple[TrainedOpponent, dict] | tuple[None, None]":
    """Load a TrainedOpponent and its enemy-config dict from a checkpoint.

    Returns (None, None) if the file is missing.
    The enemy-config dict has keys: school, level, deck — ready to drop into
    env.enemies.
    """
    if not os.path.exists(checkpoint_path):
        return None, None

    from rl.model import TransformerActorCritic
    from rl.deck_builder import deck_from_card_ids
    from rl.env import (
        CARD_DIM, PLAYER_DIM, GAME_DIM, EFFECT_TOKEN_DIM, MAX_EFFECT_TOKENS,
        HAND_SIZE, MAX_PLAYERS, MAX_TOTAL_CARDS, N_TARGET_SLOTS, N_PIP_SCHOOL_ACTIONS,
    )

    ckpt   = torch.load(checkpoint_path, map_location=device)
    cfg    = ckpt.get("config", {})
    school = cfg.get("agent_school", "Fire")
    level  = cfg.get("agent_level",  100)

    deck = None
    if ckpt.get("deck_card_ids"):
        try:
            deck = deck_from_card_ids(ckpt["deck_card_ids"])
        except Exception:
            pass

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
        embed_dim            = cfg.get("embed_dim",   64),
        n_heads              = cfg.get("n_heads",      4),
        n_layers             = cfg.get("n_layers",     2),
    ).to(device)
    model.load_state_dict(ckpt["model"])

    enemy_cfg = {"school": school, "level": level, "deck": deck}
    return TrainedOpponent(model, device, max_turns), enemy_cfg
