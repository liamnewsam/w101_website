"""Four-panel W101 benchmark.

Heatmap 1 — random vs random      (full 7×7, no symmetry shortcut)
Heatmap 2 — checkpoint vs random  (row = ckpt school, col = random school)
Heatmap 3 — difference            (heatmap2 - heatmap1, shows ckpt improvement)
Heatmap 4 — checkpoint vs ckpt    (full 7×7, no symmetry shortcut)

Row = Team A (acts first).  Col = Team B.
Cell = Team A win rate.

If --max-turns is set and the turn limit is reached, Team A loses (counts as a
loss for the agent to punish stalling via pip-select spam).

All CSVs and PNGs saved to:  benchmark_results/

Usage (from back_end/):
    python full_benchmark.py
    python full_benchmark.py --games 50 --max-turns 300
    python full_benchmark.py --games 50 --only 4
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Game import Game, createBotPlayer
from Deck import DECK_MASTER
from utils import getRandomPlayerImage

SCHOOLS  = ["Fire", "Ice", "Storm", "Life", "Death", "Myth", "Balance"]
N        = len(SCHOOLS)
CKPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rl", "checkpoints")
OUT_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_results")


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _silent(fn):
    with contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        return fn()


def _make_random_bot(school: str, uid: str):
    deck = DECK_MASTER["moderate"][school]()
    return createBotPlayer(school, uid, None, school=school, deck=deck,
                           difficulty="moderate", level=100)


def _make_ckpt_player(school: str, uid: str, cfg: dict):
    """Build a Player from a checkpoint's saved config."""
    card_ids = cfg.get("deck_card_ids")
    if card_ids:
        from rl.deck_builder import deck_from_card_ids
        deck = deck_from_card_ids(card_ids)
    else:
        deck_name = (cfg.get("agent_deck_name") or "").lower()
        tier = "simple" if "simple" in deck_name else "moderate"
        deck = DECK_MASTER[tier][school]()
    level = cfg.get("agent_level", 100)
    return createBotPlayer(school, uid, None, school=school, deck=deck,
                           difficulty="moderate", level=level)


def _load_checkpoints(filename: str = "best.pt") -> dict[str, tuple]:
    """Return {school: (TrainedOpponent, cfg_dict)} for every checkpoint found."""
    import torch
    from rl.opponent import load_opponent

    loaded = {}
    for school in SCHOOLS:
        path = os.path.join(CKPT_DIR, school, filename)
        if not os.path.exists(path):
            print(f"  [skip] no {filename} for {school}")
            continue
        opp, _ = load_opponent(path, "cpu")
        if opp is None:
            print(f"  [skip] failed to load {path}")
            continue
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        cfg  = ckpt.get("config", {})
        cfg["deck_card_ids"] = ckpt.get("deck_card_ids")
        loaded[school] = (opp, cfg)
        print(f"  Loaded {school:8s}  iter={ckpt.get('iteration', '?')}")
    return loaded


def _safe_pass(game, players):
    for p in players:
        if game.player_actions.get(p.user_id) is None:
            game.player_pass(p)


def _run_game_loop(game, players, max_turns: int | None) -> str:
    """Run a fully-constructed game to completion.

    Returns 'A' or 'B'.  If max_turns is set and the limit is reached,
    returns 'B' (Team A loses) to punish stalling.
    """
    _silent(game.begin)
    turns = 0
    while game.winner is None:
        if max_turns is not None and turns >= max_turns:
            return "B"
        if not game.allActionsReceived():
            _safe_pass(game, players)
        _silent(game.resolve_actions)
        _silent(game.start_turn)
        turns += 1
    return game.winner


# ─────────────────────────────────────────────────────────────────────────────
# Per-matchup game runners
# ─────────────────────────────────────────────────────────────────────────────

def game_random_vs_random(school_a: str, school_b: str,
                           max_turns: int | None) -> str:
    pa = _make_random_bot(school_a, "pa")
    pb = _make_random_bot(school_b, "pb")
    game = Game([pa], [pb])
    return _run_game_loop(game, [pa, pb], max_turns)


def game_ckpt_vs_random(school_a: str, opp_a, cfg_a: dict,
                         school_b: str, max_turns: int | None) -> str:
    pa = _make_ckpt_player(school_a, "pa", cfg_a)
    pb = _make_random_bot(school_b, "pb")
    game = Game([pa], [pb])
    opp_a.attach(game, pa, own_team_idx=0)
    return _run_game_loop(game, [pa, pb], max_turns)


def game_ckpt_vs_ckpt(school_a: str, opp_a, cfg_a: dict,
                       school_b: str, opp_b, cfg_b: dict,
                       max_turns: int | None) -> str:
    pa = _make_ckpt_player(school_a, "pa", cfg_a)
    pb = _make_ckpt_player(school_b, "pb", cfg_b)
    game = Game([pa], [pb])
    opp_a.attach(game, pa, own_team_idx=0)
    opp_b.attach(game, pb, own_team_idx=1)
    return _run_game_loop(game, [pa, pb], max_turns)


# ─────────────────────────────────────────────────────────────────────────────
# Full matrix runners
# ─────────────────────────────────────────────────────────────────────────────

def build_random_vs_random(games: int, max_turns: int | None) -> np.ndarray:
    """Full 7×7: random[i][j] = school_i win rate (first mover) vs school_j."""
    matrix = np.zeros((N, N))
    total  = N * N
    done   = 0
    for i, sa in enumerate(SCHOOLS):
        for j, sb in enumerate(SCHOOLS):
            wins = sum(
                1 for _ in range(games)
                if game_random_vs_random(sa, sb, max_turns) == "A"
            )
            matrix[i, j] = wins / games
            done += 1
            print(f"  [{done:2d}/{total}] rand {sa:8s} vs rand {sb:8s}  "
                  f"wins={wins}/{games}  ({matrix[i,j]:.2f})")
    return matrix


def build_ckpt_vs_random(checkpoints: dict, games: int,
                          max_turns: int | None) -> np.ndarray:
    """7×7: ckpt[i][j] = checkpoint_i win rate vs random_j."""
    matrix = np.full((N, N), np.nan)
    total  = sum(1 for s in SCHOOLS if s in checkpoints) * N
    done   = 0
    for i, sa in enumerate(SCHOOLS):
        if sa not in checkpoints:
            continue
        opp_a, cfg_a = checkpoints[sa]
        for j, sb in enumerate(SCHOOLS):
            wins = sum(
                1 for _ in range(games)
                if game_ckpt_vs_random(sa, opp_a, cfg_a, sb, max_turns) == "A"
            )
            matrix[i, j] = wins / games
            done += 1
            print(f"  [{done:2d}/{total}] ckpt {sa:8s} vs rand {sb:8s}  "
                  f"wins={wins}/{games}  ({matrix[i,j]:.2f})")
    return matrix


def build_ckpt_vs_ckpt(checkpoints: dict, games: int,
                        max_turns: int | None) -> np.ndarray:
    """Full 7×7: ckpt_ckpt[i][j] = checkpoint_i win rate (first) vs checkpoint_j."""
    matrix = np.full((N, N), np.nan)
    available = [s for s in SCHOOLS if s in checkpoints]
    total  = len(available) ** 2
    done   = 0
    for i, sa in enumerate(SCHOOLS):
        if sa not in checkpoints:
            continue
        opp_a, cfg_a = checkpoints[sa]
        for j, sb in enumerate(SCHOOLS):
            if sb not in checkpoints:
                continue
            opp_b, cfg_b = checkpoints[sb]
            wins = sum(
                1 for _ in range(games)
                if game_ckpt_vs_ckpt(sa, opp_a, cfg_a, sb, opp_b, cfg_b, max_turns) == "A"
            )
            matrix[i, j] = wins / games
            done += 1
            print(f"  [{done:2d}/{total}] ckpt {sa:8s} vs ckpt {sb:8s}  "
                  f"wins={wins}/{games}  ({matrix[i,j]:.2f})")
    return matrix


# ─────────────────────────────────────────────────────────────────────────────
# Output helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cell_text(val: float) -> str:
    return "N/A" if np.isnan(val) else f"{val:.2f}"


def _text_color(val: float) -> str:
    if np.isnan(val):
        return "gray"
    return "black" if 0.25 < val < 0.75 else "white"


def save_csv(matrix: np.ndarray, path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([""] + SCHOOLS)
        for i, school in enumerate(SCHOOLS):
            writer.writerow([school] + [_cell_text(matrix[i, j]) for j in range(N)])
    print(f"  CSV  → {path}")


def save_heatmap(matrix: np.ndarray, title: str, xlabel: str, ylabel: str,
                 path: str, games: int,
                 vmin: float = 0.0, vmax: float = 1.0,
                 cmap: str = "RdYlGn") -> None:
    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(matrix, vmin=vmin, vmax=vmax, cmap=cmap)

    ax.set_xticks(range(N))
    ax.set_yticks(range(N))
    ax.set_xticklabels(SCHOOLS, rotation=45, ha="right", fontsize=11)
    ax.set_yticklabels(SCHOOLS, fontsize=11)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(f"{title}\n({games} games per matchup)", fontsize=12)

    for i in range(N):
        for j in range(N):
            val = matrix[i, j]
            ax.text(j, i, _cell_text(val),
                    ha="center", va="center", fontsize=9,
                    color=_text_color(val))

    plt.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  PNG  → {path}")


def print_matrix(label: str, matrix: np.ndarray) -> None:
    print(f"\n── {label} ──────────────────────────────────────────")
    print(f"{'':10s}" + "".join(f"{s:>9s}" for s in SCHOOLS))
    for i, sa in enumerate(SCHOOLS):
        print(f"{sa:10s}" + "".join(f"{'N/A':>9s}" if np.isnan(matrix[i, j])
                                     else f"{matrix[i,j]:9.2f}"
                                     for j in range(N)))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="W101 full benchmark (4 heatmaps)")
    parser.add_argument("--games",     type=int, default=50,
                        help="Games per ordered matchup (default: 50)")
    parser.add_argument("--max-turns", type=int, default=None,
                        help="Turn limit per game; reaching it counts as a Team A loss "
                             "(default: no limit)")
    parser.add_argument("--only",      type=int, choices=[1, 2, 3, 4, 5], default=None,
                        help="Run only a single heatmap: 1=rand/rand, 2=best/rand, "
                             "3=difference, 4=best/best, 5=phase1/rand  (default: run all)")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    g, t, only = args.games, args.max_turns, args.only

    turns_label = f"max {t} turns" if t else "no turn limit"

    # ── Load best.pt checkpoints (needed for heatmaps 2, 3, 4) ─────────────
    checkpoints = {}
    if only not in (1, 5):
        print("\n=== Loading best.pt checkpoints ===")
        checkpoints = _load_checkpoints("best.pt")
        print(f"  {len(checkpoints)}/{N} loaded\n")

    # ── Load phase1_final.pt checkpoints (needed for heatmap 5) ─────────────
    phase1_checkpoints = {}
    if only in (None, 5):
        print("\n=== Loading phase1_final.pt checkpoints ===")
        phase1_checkpoints = _load_checkpoints("phase1_final.pt")
        print(f"  {len(phase1_checkpoints)}/{N} loaded\n")

    n_ckpt = len(checkpoints)

    # Placeholders so --only 3 can still compute the diff if called standalone
    m_rand = m_ckpt = None

    # ── Heatmap 1: random vs random ─────────────────────────────────────────
    if only in (None, 1, 3):
        print(f"=== Heatmap 1: random vs random  ({N*N} matchups × {g} games, {turns_label}) ===")
        m_rand = build_random_vs_random(g, t)
        print_matrix("Random vs Random", m_rand)
        save_csv(m_rand, os.path.join(OUT_DIR, "random_vs_random.csv"))
        save_heatmap(m_rand,
                     title="Random bot win rates (full 7×7, row goes first)",
                     xlabel="Opponent school (Team B)",
                     ylabel="Agent school (Team A)",
                     path=os.path.join(OUT_DIR, "random_vs_random.png"),
                     games=g)

    # ── Heatmap 2: checkpoint vs random ─────────────────────────────────────
    if only in (None, 2, 3):
        print(f"\n=== Heatmap 2: checkpoint vs random  ({n_ckpt*N} matchups × {g} games, {turns_label}) ===")
        m_ckpt = build_ckpt_vs_random(checkpoints, g, t)
        print_matrix("Checkpoint vs Random", m_ckpt)
        save_csv(m_ckpt, os.path.join(OUT_DIR, "ckpt_vs_random.csv"))
        save_heatmap(m_ckpt,
                     title="Checkpoint win rates vs random bots (row = checkpoint)",
                     xlabel="Random-bot opponent school",
                     ylabel="Checkpoint school (Team A)",
                     path=os.path.join(OUT_DIR, "ckpt_vs_random.png"),
                     games=g)

    # ── Heatmap 3: difference ───────────────────────────────────────────────
    if only in (None, 3):
        if m_rand is not None and m_ckpt is not None:
            print(f"\n=== Heatmap 3: difference (ckpt_vs_random − random_vs_random) ===")
            m_diff = m_ckpt - m_rand
            print_matrix("Difference (ckpt − rand)", m_diff)
            save_csv(m_diff, os.path.join(OUT_DIR, "difference.csv"))
            save_heatmap(m_diff,
                         title="Improvement: checkpoint over random bot\n(positive = checkpoint wins more)",
                         xlabel="Opponent school",
                         ylabel="School",
                         path=os.path.join(OUT_DIR, "difference.png"),
                         games=g,
                         vmin=-0.5, vmax=0.5,
                         cmap="RdYlGn")
        else:
            print("\n[skip] Heatmap 3 requires both heatmaps 1 and 2 — rerun without --only.")

    # ── Heatmap 4: checkpoint vs checkpoint ─────────────────────────────────
    if only in (None, 4):
        print(f"\n=== Heatmap 4: checkpoint vs checkpoint  ({n_ckpt*n_ckpt} matchups × {g} games, {turns_label}) ===")
        m_cc = build_ckpt_vs_ckpt(checkpoints, g, t)
        print_matrix("Checkpoint vs Checkpoint", m_cc)
        save_csv(m_cc, os.path.join(OUT_DIR, "ckpt_vs_ckpt.csv"))
        save_heatmap(m_cc,
                     title="Checkpoint win rates (full 7×7, row goes first)",
                     xlabel="Checkpoint opponent (Team B)",
                     ylabel="Checkpoint (Team A)",
                     path=os.path.join(OUT_DIR, "ckpt_vs_ckpt.png"),
                     games=g)

    # ── Heatmap 5: phase1_final vs random ───────────────────────────────────
    if only in (None, 5):
        n_p1 = len(phase1_checkpoints)
        print(f"\n=== Heatmap 5: phase1_final vs random  ({n_p1*N} matchups × {g} games, {turns_label}) ===")
        m_p1 = build_ckpt_vs_random(phase1_checkpoints, g, t)
        print_matrix("Phase1 vs Random", m_p1)
        save_csv(m_p1, os.path.join(OUT_DIR, "phase1_vs_random.csv"))
        save_heatmap(m_p1,
                     title="phase1_final win rates vs random bots (row = checkpoint)",
                     xlabel="Random-bot opponent school",
                     ylabel="phase1_final school (Team A)",
                     path=os.path.join(OUT_DIR, "phase1_vs_random.png"),
                     games=g)

    print(f"\nAll results saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
