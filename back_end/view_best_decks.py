"""View the top-5 saved evolutionary decks for a school.

Usage (from back_end/):
    python view_best_decks.py
    python view_best_decks.py --school Ice
    python view_best_decks.py --dir rl/checkpoints/evolutionary/Fire/best_decks
"""
from __future__ import annotations

import argparse
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Card import CARD_BY_ID


def view(deck_dir: str) -> None:
    files = sorted(f for f in os.listdir(deck_dir) if f.startswith("deck_") and f.endswith(".pt"))
    if not files:
        print(f"No deck files found in {deck_dir}")
        return

    for fname in files:
        path = os.path.join(deck_dir, fname)
        data = torch.load(path, map_location="cpu")

        rank     = fname.replace("deck_", "").replace(".pt", "")
        win_rate = data.get("win_rate", 0.0)
        wins     = data.get("wins", "?")
        games    = data.get("games", "?")
        iteration= data.get("iteration", "?")
        gen      = data.get("generation", "?")

        print(f"\n{'─'*55}")
        print(f"  Rank #{rank}  |  win rate: {win_rate:.2%}  ({wins}/{games})  "
              f"|  iter {iteration}  gen {gen}")
        print(f"{'─'*55}")

        card_ids = data.get("deck_card_ids", [])
        # Group duplicates
        counts: dict[str, int] = {}
        for cid in card_ids:
            counts[cid] = counts.get(cid, 0) + 1

        # Sort by pip cost then name
        def sort_key(cid):
            cd = CARD_BY_ID.get(cid)
            if cd is None:
                return (99, cid)
            pip = cd.pips if isinstance(cd.pips, (int, float)) else 99
            return (pip, cd.name)

        for cid in sorted(counts, key=sort_key):
            cd    = CARD_BY_ID.get(cid)
            name  = cd.name   if cd else cid
            pips  = cd.pips   if cd else "?"
            school= cd.school if cd else "?"
            qty   = counts[cid]
            print(f"  {'x'+str(qty):<4} {str(pips)+'p':<6} [{school:<8}]  {name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--school", "-s", type=str, default="Fire")
    parser.add_argument("--dir",    "-d", type=str, default=None,
                        help="Direct path to best_decks directory")
    args = parser.parse_args()

    deck_dir = args.dir or f"rl/checkpoints/{args.school}/best_decks"
    if not os.path.isdir(deck_dir):
        # Try evolutionary subdirectory
        deck_dir = f"rl/checkpoints/evolutionary/{args.school}/best_decks"

    if not os.path.isdir(deck_dir):
        print(f"Directory not found: {deck_dir}")
        return

    print(f"Loading decks from: {deck_dir}")
    view(deck_dir)
    print()


if __name__ == "__main__":
    main()
