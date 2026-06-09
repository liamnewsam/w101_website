#!/usr/bin/env python3
"""
set_user_level.py — Set a player's display level for a specific school (or all schools).

Level is derived from per-school ELO: level = clamp(10, 170, (elo - 100) // 32 + 10)
This script sets school_elos for the given school to produce the target level.

Usage:
    python set_user_level.py <username> <school> <level>
    python set_user_level.py <username> all <level>

Examples:
    python set_user_level.py Liam fire 10
    python set_user_level.py Liam balance 40
    python set_user_level.py Liam all 50

Valid schools: fire, ice, storm, life, death, myth, balance, all
Valid level range: 10–170
"""

import sys
from database import SessionLocal
from sqlalchemy.orm.attributes import flag_modified
from models import User, PlayerState, SCHOOLS_LIST, _ELO_FLOOR, _ELO_PER_LEVEL, _SCHOOL_LEVEL_MIN, _SCHOOL_LEVEL_MAX


def level_to_elo(level: int) -> int:
    level = max(_SCHOOL_LEVEL_MIN, min(_SCHOOL_LEVEL_MAX, level))
    return _ELO_FLOOR + (level - _SCHOOL_LEVEL_MIN) * _ELO_PER_LEVEL


def set_user_school_level(username: str, school: str, level: int) -> None:
    school = school.lower()
    schools = SCHOOLS_LIST if school == "all" else [school]

    for s in schools:
        if s not in SCHOOLS_LIST:
            print(f"Error: unknown school '{s}'. Valid: {', '.join(SCHOOLS_LIST)}, all")
            sys.exit(1)

    if not (_SCHOOL_LEVEL_MIN <= level <= _SCHOOL_LEVEL_MAX):
        print(f"Error: level must be between {_SCHOOL_LEVEL_MIN} and {_SCHOOL_LEVEL_MAX} (got {level})")
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

        elo_needed = level_to_elo(level)
        school_elos = dict(state.school_elos or {})

        for s in schools:
            old_level = state._compute_school_level(s)
            school_elos[s] = elo_needed
            state.school_elos = school_elos
            flag_modified(state, "school_elos")
            db.commit()
            db.refresh(state)
            new_level = state._compute_school_level(s)
            print(f"Updated '{username}' [{s}]: level {old_level} -> {new_level} (elo={elo_needed})")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    username_arg = sys.argv[1]
    school_arg = sys.argv[2]
    try:
        level_arg = int(sys.argv[3])
    except ValueError:
        print(f"Error: level must be an integer (got '{sys.argv[3]}')")
        sys.exit(1)

    set_user_school_level(username_arg, school_arg, level_arg)
