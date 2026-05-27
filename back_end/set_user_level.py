#!/usr/bin/env python3
"""
set_user_level.py — Update a user's level in the database.

Level is derived from ELO: level = max(1, min(100, (elo - 100) // 50 + 1))
This script computes the ELO needed for the target level and writes it.

Usage:
    python set_user_level.py <username> <level>

Examples:
    python set_user_level.py Liam 10
    python set_user_level.py "GuestUser" 50
"""

import sys
from database import SessionLocal
from models import User, PlayerState


def level_to_elo(level: int) -> int:
    level = max(1, min(100, level))
    return (level - 1) * 50 + 100


def set_user_level(username: str, level: int) -> None:
    if not (1 <= level <= 100):
        print(f"Error: level must be between 1 and 100 (got {level})")
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

        old_level = state._compute_level()
        new_elo = level_to_elo(level)

        state.elo = new_elo
        db.commit()
        db.refresh(state)

        print(f"Updated '{username}': level {old_level} -> {state._compute_level()} (elo={state.elo})")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    username_arg = sys.argv[1]
    try:
        level_arg = int(sys.argv[2])
    except ValueError:
        print(f"Error: level must be an integer (got '{sys.argv[2]}')")
        sys.exit(1)

    set_user_level(username_arg, level_arg)
