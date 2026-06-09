#!/usr/bin/env python3
"""
add_deck.py — Add a deck to a player's deck list.

── From a DECK_MASTER tier ──────────────────────────────────────────────────
    python add_deck.py <username> <tier> <school>
    python add_deck.py <username> <tier> all

    Examples:
        python add_deck.py Liam hard life
        python add_deck.py Liam starter storm
        python add_deck.py Liam hard all

    Valid tiers:   moderate, hard, starter, easy
    Valid schools: fire, ice, storm, life, death, myth, balance, all

── From an RL checkpoint ────────────────────────────────────────────────────
    python add_deck.py <username> --checkpoint <path> [--name <deck_name>]

    Examples:
        python add_deck.py Liam --checkpoint rl/checkpoints/model_00050.pt
        python add_deck.py Liam --checkpoint rl/checkpoints/model_00050.pt --name "Fire Agent v1"

── From a directory of RL checkpoints ───────────────────────────────────────
    python add_deck.py <username> --checkpoint-dir <directory>

    Loads every deck_*.pt file in the directory (sorted) and adds each as a
    separate deck.

    Examples:
        python add_deck.py Liam --checkpoint-dir rl/checkpoints/evolutionary/Fire/best_decks
"""

import sys
from database import SessionLocal
from sqlalchemy.orm.attributes import flag_modified
from models import User, PlayerState, SCHOOLS_LIST
from Deck import DECK_MASTER


VALID_TIERS = list(DECK_MASTER.keys())


def add_deck_to_user(username: str, tier: str, school: str) -> None:
    tier = tier.lower()
    school = school.lower()
    schools = SCHOOLS_LIST if school == "all" else [school]

    if tier not in VALID_TIERS:
        print(f"Error: unknown tier '{tier}'. Valid: {', '.join(VALID_TIERS)}")
        sys.exit(1)

    for s in schools:
        if s not in SCHOOLS_LIST:
            print(f"Error: unknown school '{s}'. Valid: {', '.join(SCHOOLS_LIST)}, all")
            sys.exit(1)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            print(f"Error: no user found with username '{username}'")
            sys.exit(1)

        state = db.query(PlayerState).filter(PlayerState.player_id == str(user.id)).first()
        if state is None:
            print(f"Error: no player state found for user '{username}' (id={user.id})")
            sys.exit(1)

        decks = list(state.decks or [])
        for s in schools:
            school_key = s.capitalize()
            deck_fn = DECK_MASTER[tier].get(school_key)
            if deck_fn is None:
                print(f"Error: no '{tier}' deck found for school '{s}'")
                sys.exit(1)
            deck_dict = deck_fn().to_dict()
            decks.append(deck_dict)
            print(f"Added '{deck_dict['name']}' to '{username}'")

        state.decks = decks
        flag_modified(state, "decks")
        db.commit()
        print(f"'{username}' now has {len(decks)} deck(s)")
    finally:
        db.close()


def add_checkpoint_dir_to_user(username: str, directory: str) -> None:
    import torch
    from pathlib import Path

    dirpath = Path(directory)
    checkpoints = sorted(dirpath.glob("deck_*.pt"))
    if not checkpoints:
        print(f"Error: no deck_*.pt files found in '{directory}'")
        sys.exit(1)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            print(f"Error: no user found with username '{username}'")
            sys.exit(1)

        state = db.query(PlayerState).filter(PlayerState.player_id == str(user.id)).first()
        if state is None:
            print(f"Error: no player state found for user '{username}' (id={user.id})")
            sys.exit(1)

        decks = list(state.decks or [])
        for ckpt_path in checkpoints:
            ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
            card_ids = ckpt.get("deck_card_ids")
            if not card_ids:
                print(f"Warning: '{ckpt_path.name}' has no deck_card_ids — skipping")
                continue
            cfg = ckpt.get("config", {})
            iteration = ckpt.get("iteration", 0)
            school = cfg.get("agent_school", "Unknown")
            deck_name = f"Agent {school} (iter {iteration}) [{ckpt_path.stem}]"
            decks.append({"name": deck_name, "card_ids": card_ids})
            print(f"  Added '{deck_name}' ({len(card_ids)} cards)")

        state.decks = decks
        flag_modified(state, "decks")
        db.commit()
        print(f"'{username}' now has {len(decks)} deck(s)")
    finally:
        db.close()


def add_checkpoint_deck_to_user(username: str, checkpoint_path: str, deck_name: str | None = None) -> None:
    import torch
    from pathlib import Path

    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    card_ids = ckpt.get("deck_card_ids")
    if not card_ids:
        print(f"Error: checkpoint '{checkpoint_path}' has no saved deck_card_ids.")
        sys.exit(1)

    cfg = ckpt.get("config", {})
    if deck_name is None:
        iteration = ckpt.get("iteration", 0)
        school = cfg.get("agent_school", "Unknown")
        deck_name = f"Agent {school} (iter {iteration})"

    deck_dict = {"name": deck_name, "card_ids": card_ids}

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            print(f"Error: no user found with username '{username}'")
            sys.exit(1)

        state = db.query(PlayerState).filter(PlayerState.player_id == str(user.id)).first()
        if state is None:
            print(f"Error: no player state found for user '{username}' (id={user.id})")
            sys.exit(1)

        decks = list(state.decks or [])
        decks.append(deck_dict)
        state.decks = decks
        flag_modified(state, "decks")
        db.commit()
        print(f"Added '{deck_name}' ({len(card_ids)} cards) to '{username}'")
        print(f"'{username}' now has {len(decks)} deck(s)")
    finally:
        db.close()


if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) >= 2 and "--checkpoint-dir" in args:
        username = args[0]
        cd_idx = args.index("--checkpoint-dir")
        if cd_idx + 1 >= len(args):
            print("Error: --checkpoint-dir requires a path argument")
            sys.exit(1)
        add_checkpoint_dir_to_user(username, args[cd_idx + 1])
    elif len(args) >= 2 and "--checkpoint" in args:
        username = args[0]
        cp_idx = args.index("--checkpoint")
        if cp_idx + 1 >= len(args):
            print("Error: --checkpoint requires a path argument")
            sys.exit(1)
        checkpoint_path = args[cp_idx + 1]
        name = None
        if "--name" in args:
            n_idx = args.index("--name")
            if n_idx + 1 < len(args):
                name = args[n_idx + 1]
        add_checkpoint_deck_to_user(username, checkpoint_path, name)
    elif len(args) == 3:
        add_deck_to_user(args[0], args[1], args[2])
    else:
        print(__doc__)
        sys.exit(1)
