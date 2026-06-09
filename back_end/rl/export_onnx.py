"""Convert all .pt checkpoints to ONNX + JSON sidecars.

Run once locally (requires PyTorch):
    cd back_end
    python -m rl.export_onnx
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import torch

from rl.model import TransformerActorCritic
from rl.env import (
    CARD_DIM, PLAYER_DIM, GAME_DIM, EFFECT_TOKEN_DIM,
    MAX_EFFECT_TOKENS, HAND_SIZE, MAX_PLAYERS, MAX_TOTAL_CARDS,
    N_TARGET_SLOTS, N_PIP_SCHOOL_ACTIONS, N_ACTIONS,
)

_CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"


def export_checkpoint(pt_path: str) -> None:
    pt_path   = Path(pt_path)
    onnx_path = pt_path.with_suffix(".onnx")
    json_path = pt_path.with_suffix(".json")

    ckpt = torch.load(str(pt_path), map_location="cpu", weights_only=False)
    cfg  = ckpt.get("config", {})

    json_path.write_text(json.dumps({
        "path":            str(pt_path),
        "filename":        pt_path.name,
        "iteration":       ckpt.get("iteration", 0),
        "agent_school":    cfg.get("agent_school", "Unknown"),
        "agent_level":     cfg.get("agent_level", 1),
        "agent_deck_name": cfg.get("agent_deck_name"),
        "embed_dim":       cfg.get("embed_dim", 64),
        "n_heads":         cfg.get("n_heads", 4),
        "n_layers":        cfg.get("n_layers", 2),
        "deck_card_ids":   ckpt.get("deck_card_ids", []),
    }, indent=2))

    if "model" not in ckpt:
        print(f"  OK  {pt_path.name} (deck-only, no ONNX needed)")
        return

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
    )
    model.load_state_dict(ckpt["model"])
    model.eval()

    dummy = (
        torch.zeros(1, MAX_TOTAL_CARDS,    CARD_DIM),
        torch.zeros(1, MAX_PLAYERS,        PLAYER_DIM),
        torch.zeros(1, MAX_EFFECT_TOKENS,  EFFECT_TOKEN_DIM),
        torch.zeros(1, GAME_DIM),
        torch.ones (1, N_ACTIONS),
    )

    torch.onnx.export(
        model, dummy, str(onnx_path),
        input_names  = ["cards", "players", "effects", "game", "action_mask"],
        output_names = ["logits", "value"],
        opset_version = 17,
    )
    print(f"  OK  {pt_path.name}")


def main() -> None:
    pts = sorted(glob.glob(str(_CHECKPOINT_DIR / "**" / "*.pt"), recursive=True))
    if not pts:
        print("No .pt files found in", _CHECKPOINT_DIR)
        return
    print(f"Exporting {len(pts)} checkpoints...")
    for pt in pts:
        try:
            export_checkpoint(pt)
        except Exception as e:
            print(f"  FAIL {os.path.basename(pt)}: {e}")
    print("Done.")


if __name__ == "__main__":
    main()
