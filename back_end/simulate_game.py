"""Simulate a bot-vs-bot game and optionally save the replay to a user's history.

─────────────────────────────────────────────
CONFIGURATION
─────────────────────────────────────────────
Edit TEAM_A_CONFIG and TEAM_B_CONFIG below to set up both teams.

Each player dict accepts:
    name        (str)  – display name
    school      (str)  – "Fire", "Ice", "Storm", "Life", "Death", "Myth", "Balance"
    level       (int)  – player level (affects base stats)
    deck        (str|None)
                       – deck tier to use: "simple", "moderate", or None for moderate default.
                         The deck matching (tier, school) is picked automatically.
    model_path  (str|None)
                       – path to a checkpoint .pt file.  None → random bot.

─────────────────────────────────────────────
OUTPUT
─────────────────────────────────────────────
    --output   path/to/game_log.txt      write a human-readable action log
    --save-to  username                  save full replay to that user's game history

Usage:
    cd back_end
    python simulate_game.py --output game_log.txt --save-to myusername
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════════
# TEAM CONFIGURATION  ← edit this section
# ══════════════════════════════════════════════════════════════════════════════

TEAM_A_CONFIG = [
    {
        "name":       "Balance100",
        "school":     "Balance",
        "level":      100,
        "deck":       None,      # "simple" | "moderate" | None
        "model_path": "rl/checkpoints/Balance/best.pt",
    },
]

TEAM_B_CONFIG = [
    {
        "name":       "RandomBot",
        "school":     "Fire",
        "level":      100,
        "deck":       "moderate",      # "simple" | "moderate" | None
        "model_path": None
    },
]

# Maximum number of turns before the game is declared a draw
MAX_TURNS = 300

# ══════════════════════════════════════════════════════════════════════════════
# Implementation
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_cfg(cfg: dict) -> tuple[dict, dict | None]:
    """Return (resolved_cfg, model_meta).

    Any of school/level/deck left as None are filled from the checkpoint's
    config dict when a model_path is provided.  model_meta is None if no
    model_path is given.
    """
    path = cfg.get("model_path")
    meta = None

    if path:
        from rl.inference import load_model
        _, meta = load_model(path)

    resolved = dict(cfg)
    if meta:
        if resolved.get("school") is None:
            resolved["school"] = meta.get("agent_school", "Balance")
        if resolved.get("level") is None:
            resolved["level"] = meta.get("agent_level", 1)
        if resolved.get("deck") is None:
            card_ids = meta.get("deck_card_ids")
            if card_ids:
                from rl.deck_builder import deck_from_card_ids
                resolved["deck"] = deck_from_card_ids(card_ids)
            elif meta.get("agent_deck_name"):
                deck_name = meta["agent_deck_name"].lower()
                resolved["deck"] = "simple" if "simple" in deck_name else "moderate"

    # Final hardcoded fallbacks
    if resolved.get("school") is None:
        resolved["school"] = "Balance"
    if resolved.get("level") is None:
        resolved["level"] = 1

    return resolved, meta


def _build_player(cfg: dict, uid: str):
    from Game import createBotPlayer
    from Deck import DECK_MASTER
    from utils import getRandomPlayerImage

    school   = cfg["school"]
    level    = cfg.get("level", 1)
    name     = cfg.get("name", uid)
    deck_cfg = cfg.get("deck") or "moderate"

    if isinstance(deck_cfg, str):
        tier_map = DECK_MASTER.get(deck_cfg)
        deck = tier_map[school]() if (tier_map and school in tier_map) else None
    else:
        deck = deck_cfg  # pre-built Deck object from deck_builder checkpoint

    return createBotPlayer(name, uid, getRandomPlayerImage(),
                           school=school, deck=deck, difficulty="easy", level=level)


def _format_log_entry(entry: dict) -> str:
    t = entry.get("type", "?")
    if t == "turn_end":
        return f"[turn_end] resting: {entry.get('resting_player', '?')}"
    if t == "result":
        res = entry.get("result", "?")
        if res == "dead":
            return f"[result] {entry.get('player', '?')} is dead"
        if res == "success":
            card = entry.get("card", "?")
            return f"[result] {entry.get('player', '?')} cast {card}"
        return f"[result] {res}"
    if t == "action":
        act = entry.get("action", "?")
        pid = entry.get("player", "?")
        if act == "discard":
            card = entry.get("card", f"slot {entry.get('cardIndex', '?')}")
            return f"[discard] {pid} discards {card}"
        if act == "pip_school_change":
            return f"[pip_school] {pid} → {entry.get('school', '?')}"
        return (f"[action] {pid} {act} "
                f"card={entry.get('cardIndex', '')} target={entry.get('target', '')}")
    if t == "effect_resolve":
        asp = entry.get("aspect", "?")
        if asp == "damage":
            return (f"[dmg] {entry.get('player', '?')} → {entry.get('target', '?')} "
                    f"{int(entry.get('amount', 0))} {entry.get('school', '')} dmg")
        if asp == "heal":
            return (f"[heal] {entry.get('player', '?')} → {entry.get('target', '?')} "
                    f"+{int(entry.get('amount', 0))} hp")
        if asp == "pip_gain":
            return f"[pip] {entry.get('target', '?')} gains {entry.get('amount', {})}"
        return f"[{asp}] {json.dumps({k: v for k, v in entry.items() if k != 'type'})}"
    return f"[{t}] {json.dumps({k: v for k, v in entry.items() if k != 'type'})}"


def _write_txt_log(game, all_turns: list[dict], output_path: str):
    lines = []
    lines.append(f"W101 Simulated Game — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Winner: Team {game.winner}")
    lines.append(f"Total turns: {game.turns}")
    lines.append("")

    for team_idx, team in enumerate(game.teams):
        label = "A" if team_idx == 0 else "B"
        lines.append(f"Team {label}:")
        for p in team:
            lines.append(f"  {p.name} ({p.school}, Lv{p.maxHealth // 30}) — HP: {int(p.health)}/{p.maxHealth}")
        lines.append("")

    for turn_num, turn in enumerate(all_turns, 1):
        lines.append(f"── Turn {turn_num} ──────────────────────────")
        for entry in turn.get("log", []):
            lines.append("  " + _format_log_entry(entry))
        lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Log written to: {output_path}")


def _save_to_user(game, all_turns: list[dict], initial_state: dict, username: str):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from database import SessionLocal
    from models import User, PlayerState, GameLog

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            print(f"[save] User '{username}' not found — replay not saved.")
            return

        game_id = uuid.uuid4().hex[:8]

        # Build a minimal match result players list
        players_data = []
        for team_idx, team in enumerate(game.teams):
            label = "A" if team_idx == 0 else "B"
            for p in team:
                players_data.append({
                    "id": p.user_id,
                    "name": p.name,
                    "team": label,
                    "school": p.school,
                    "level": getattr(p, "_sim_level", 1),
                    "isBot": True,
                    "elo": 0,
                    "elo_change": 0,
                    "image_path": getattr(p, "img_path", ""),
                })

        log_entry = GameLog(
            game_id=game_id,
            winner=game.winner,
            player_ids=[str(user.id)],
            players=players_data,
            initial_game_state=initial_state,
            turns=all_turns,
        )
        db.add(log_entry)
        db.commit()
        print(f"Replay saved as game_id={game_id} for user '{username}'")
    except Exception as e:
        print(f"[save] Error saving replay: {e}")
        db.rollback()
    finally:
        db.close()


def _prepare_log(log: list) -> None:
    """Replace card ID strings with img_path strings in result entries (mirrors app.py prepareLog)."""
    from Card import CARD_BY_ID
    for entry in log:
        if entry.get("type") == "result" and entry.get("result") == "success":
            card_id = entry.get("card")
            if card_id and card_id in CARD_BY_ID:
                entry["card"] = CARD_BY_ID[card_id].img_path


def run_simulation(output_txt: str | None = None, save_to_user: str | None = None):
    import json as _json
    from Game import Game

    print("Building teams...")
    teamA, teamB = [], []

    # (player, TrainedOpponent, own_team_idx) — wired into game after construction
    trained_opponents = []

    for i, cfg in enumerate(TEAM_A_CONFIG):
        uid = f"A_{i}_{uuid.uuid4().hex[:4]}"
        resolved, meta = _resolve_cfg(cfg)
        player = _build_player(resolved, uid)
        player._sim_level = resolved.get("level", 1)
        teamA.append(player)
        if cfg.get("model_path") and meta:
            from rl.opponent import load_opponent
            opp, _ = load_opponent(cfg["model_path"], "cpu", max_turns=MAX_TURNS)
            if opp:
                trained_opponents.append((player, opp, 0))
                print(f"  Loaded model for {resolved['name']} "
                      f"(school={resolved['school']}, level={resolved['level']}, "
                      f"iter={meta.get('iteration')})")

    for i, cfg in enumerate(TEAM_B_CONFIG):
        uid = f"B_{i}_{uuid.uuid4().hex[:4]}"
        resolved, meta = _resolve_cfg(cfg)
        player = _build_player(resolved, uid)
        player._sim_level = resolved.get("level", 1)
        teamB.append(player)
        if cfg.get("model_path") and meta:
            from rl.opponent import load_opponent
            opp, _ = load_opponent(cfg["model_path"], "cpu", max_turns=MAX_TURNS)
            if opp:
                trained_opponents.append((player, opp, 1))
                print(f"  Loaded model for {resolved['name']} "
                      f"(school={resolved['school']}, level={resolved['level']}, "
                      f"iter={meta.get('iteration')})")

    print(f"Team A: {[p.name for p in teamA]}")
    print(f"Team B: {[p.name for p in teamB]}")
    print(f"Model bots: {[p.name for p, _, _ in trained_opponents]}")
    print("Starting game...\n")

    game = Game(teamA, teamB)
    for player, opp, team_idx in trained_opponents:
        opp.attach(game, player, own_team_idx=team_idx)

    import io, contextlib

    def silent(fn):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn()

    silent(game.begin)
    initial_state = _json.loads(_json.dumps(game.to_json_public()))

    all_turns = []
    turn_count = 0

    while not game.winner and turn_count < MAX_TURNS:
        if not game.allActionsReceived():
            # Shouldn't happen in all-bot games, but safeguard
            print("[warn] Actions not received — forcing pass for stuck bots")
            for p in game.current_team(aliveOnly=True):
                if game.player_actions.get(p.user_id) is None:
                    game.player_pass(p)

        turn_log = silent(game.resolve_actions)
        if turn_log is None:
            turn_log = []

        next_log = silent(game.start_turn)
        if next_log:
            turn_log.extend(next_log)

        _prepare_log(turn_log)
        final_state = _json.loads(_json.dumps(game.to_json_public()))
        all_turns.append({"log": turn_log, "finalGameState": final_state})

        if game.winner:
            break

        turn_count += 1

    winner = game.winner or "Draw"
    print(f"Game over! Winner: Team {winner}  ({game.turns} turns)")

    # Print final HP
    for team_idx, team in enumerate(game.teams):
        label = "A" if team_idx == 0 else "B"
        for p in team:
            print(f"  [{label}] {p.name}: {int(p.health)}/{p.maxHealth} HP")

    if output_txt:
        _write_txt_log(game, all_turns, output_txt)

    if save_to_user:
        _save_to_user(game, all_turns, initial_state, save_to_user)

    return game, all_turns


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate a W101 bot game")
    parser.add_argument("--output",   metavar="PATH",     help="Write human-readable log to this .txt file")
    parser.add_argument("--save-to",  metavar="USERNAME",  dest="save_to", help="Save replay to this user's history")
    args = parser.parse_args()

    run_simulation(output_txt=args.output, save_to_user=args.save_to)
