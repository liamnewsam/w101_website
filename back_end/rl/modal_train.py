"""Modal training launcher for the W101 RL agent.

════════════════════════════════════════════════════════
ASYNC TRAINING (survives closing your laptop)
════════════════════════════════════════════════════════

`modal run` ties the job to your local process — closing your terminal
cancels training even with --detach. The fix is to deploy the app once
so Modal owns the lifecycle, then trigger via the web endpoint.

── One-time setup ────────────────────────────────────────
    modal deploy rl/modal_train.py
    # Prints a URL like:
    # https://<workspace>--w101-rl-training-start-training.modal.run

── Start training (fire and forget) ──────────────────────
    python rl/modal_train.py --school Fire
    python rl/modal_train.py --school Fire --iterations 300
    python rl/modal_train.py --school Life --resume Life/latest.pt

  Or with curl directly:
    curl -s -X POST <URL> -H 'Content-Type: application/json' \
         -d '{"school":"Fire","n_iterations":300}'

── Monitor / cancel ──────────────────────────────────────
    modal app logs w101-rl-training
    modal app stop w101-rl-training

── Download results ──────────────────────────────────────
    modal volume get w101-rl-checkpoints checkpoints/ rl/checkpoints/ --force
    modal volume get w101-rl-checkpoints logs/ rl/logs/ --force

── Complete volume reset ─────────────────────────────────
    # Pass reset_volume=true in the JSON body, or use the local entrypoint:
    modal run rl/modal_train.py --school Fire --reset-volume

════════════════════════════════════════════════════════
ALL PARAMS (JSON body for curl / CLI flags for python rl/modal_train.py)
════════════════════════════════════════════════════════
  school                Fire | Ice | Storm | Life | Death | Myth | Balance
  resume                Checkpoint path relative to volume checkpoints/
  reset_optimizers      Load weights only, discard Adam state  [round 2+]
  reset_volume          Wipe all checkpoints and logs before training
  opponents             Comma-separated trained opponent schools  (e.g. Storm,Ice)
  bc_coef               BC loss weight  (0.5 round 1 · 0.15 round 2)
  use_evo_deck          Use evolutionary deck builder instead of PPO
  n_iterations          PPO iterations  (default 200)
  max_turns             Turn limit per game  (default 100; try 150 for Life)
  forced_cards          Card IDs always in deck  (e.g. reshuffle)
  log                   Log filename inside volume logs/  (auto-named if omitted)
  pin_deck              Phase 1: fix deck, train PPO only; advance by win-rate
  phase1_wr_threshold   Smoothed WR to advance each curriculum sub-phase
  phase2_wr_threshold   Smoothed WR to enter phase 2 (evo deck, level 100)
  n_curriculum_phases   Sub-phases in phase 1; enemy level ramps each phase
════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import modal

# ── Paths ─────────────────────────────────────────────────────────────────────

BACK_END = Path(__file__).parent.parent.resolve()  # …/back_end  (resolved locally)
REMOTE_APP = "/app"                                 # source root inside container
REMOTE_VOL = "/checkpoints"                         # persistent volume mount point

# ── Image ─────────────────────────────────────────────────────────────────────

_SKIP_DIRS = {
    Path("rl") / "checkpoints",
    Path("rl") / "logs",
    Path("rl") / "eval",
    Path("rl") / "crashes",
}

def _ignore(path: Path) -> bool:
    """Return True to exclude a file from the container (relative to BACK_END)."""
    if any(p in {"__pycache__", ".git"} for p in path.parts):
        return True
    if path.suffix in {".pyc", ".db"}:
        return True
    for skip in _SKIP_DIRS:
        try:
            path.relative_to(skip)
            return True
        except ValueError:
            pass
    return False


image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "torch",
        "numpy",
        "gymnasium",
        "python-dotenv",
        "fastapi[standard]",
    )
    .add_local_dir(
        BACK_END,
        remote_path=REMOTE_APP,
        ignore=_ignore,
    )
)

# ── App ───────────────────────────────────────────────────────────────────────

app = modal.App("w101-rl-training")

volume = modal.Volume.from_name("w101-rl-checkpoints", create_if_missing=True)

# ── Training function ─────────────────────────────────────────────────────────

@app.function(
    image=image,
    gpu="T4",
    volumes={REMOTE_VOL: volume},
    # SECRET_KEY is required by config.py (Flask auth); not used during RL training.
    secrets=[modal.Secret.from_dict({"SECRET_KEY": "rl-training-placeholder"})],
    timeout=60 * 60 * 12,  # 12-hour max per run
)
def train_remote(
    school:           str        = "Fire",
    resume:           str | None = None,
    reset_optimizers: bool       = False,
    reset_volume:     bool       = False,
    opponents:        str        = "",
    bc_coef:          float      = 0.5,
    use_evo_deck:     bool       = False,
    evo_seed:         str        = "moderate",  # "moderate" or checkpoint path e.g. Fire/latest.pt
    n_iterations:     int        = 200,
    max_turns:        int        = 100,
    log:              str        = "",
    forced_cards:        str        = "",
    pin_deck:             bool       = False,
    phase1_wr_threshold:  float      = 0.0,
    phase2_wr_threshold:  float      = 0.0,
    n_curriculum_phases:  int        = 1,
    evo_gen_games:        int        = 240,
):
    """Run RL training on a Modal GPU. Checkpoints are saved to the volume."""
    import shutil
    import sys
    sys.path.insert(0, REMOTE_APP)
    os.chdir(REMOTE_APP)

    # Optionally wipe all previous checkpoints and logs
    if reset_volume:
        for subdir in ["checkpoints", "logs"]:
            vol_path = f"{REMOTE_VOL}/{subdir}"
            if os.path.exists(vol_path):
                shutil.rmtree(vol_path)
                print(f"  → reset: cleared {vol_path}")

    # rl/checkpoints and rl/logs are excluded from the source mount so they
    # don't exist yet. Symlink them into the persistent volume.
    for subdir in ["checkpoints", "logs"]:
        vol_path = f"{REMOTE_VOL}/{subdir}"
        local_sym = f"rl/{subdir}"
        os.makedirs(vol_path, exist_ok=True)
        if not os.path.lexists(local_sym):
            os.symlink(vol_path, local_sym)

    from rl.train import train, Config

    resume_ckpt = None
    if resume:
        # Accept absolute paths or bare relative paths like "Fire/latest.pt"
        resume_ckpt = resume if resume.startswith("/") else f"{REMOTE_VOL}/checkpoints/{resume}"
        # Strip accidental "checkpoints/" prefix if user passed it explicitly
        resume_ckpt = resume_ckpt.replace("/checkpoints/checkpoints/checkpoints/", "/checkpoints/checkpoints/")

    log_file = None
    if log:
        log_file = f"rl/logs/{log}" if not log.startswith("/") else log

    # Resolve seed deck — used for both evo (phase 2) and pin_deck (phase 1)
    evo_seed_deck = None
    if evo_seed == "moderate":
        from Deck import DECK_MASTER
        evo_seed_deck = DECK_MASTER["moderate"][school]()
    elif evo_seed:
        seed_path = evo_seed if evo_seed.startswith("/") else f"{REMOTE_VOL}/checkpoints/{evo_seed}"
        import torch as _torch
        from rl.deck_builder import deck_from_card_ids
        _ckpt = _torch.load(seed_path, map_location="cpu")
        if _ckpt.get("deck_card_ids"):
            evo_seed_deck = deck_from_card_ids(_ckpt["deck_card_ids"])
            print(f"  → seed deck loaded from {seed_path}")

    cfg = Config(
        agent_school         = school,
        n_iterations         = n_iterations,
        max_turns            = max_turns,
        resume_checkpoint    = resume_ckpt,
        reset_optimizers     = reset_optimizers,
        opponent_schools     = [s.strip() for s in opponents.split(",") if s.strip()],
        bc_coef              = bc_coef,
        use_evo_deck         = use_evo_deck,
        evo_seed_deck        = evo_seed_deck,
        log_file             = log_file,
        forced_deck_cards    = [c.strip() for c in forced_cards.split(",") if c.strip()],
        pin_deck             = pin_deck,
        phase1_wr_threshold  = phase1_wr_threshold,
        phase2_wr_threshold  = phase2_wr_threshold,
        n_curriculum_phases  = n_curriculum_phases,
        evo_gen_games        = evo_gen_games,
        phase2_evo_gen_games = evo_gen_games,
    )
    train(cfg)

    volume.commit()  # flush volume writes before the container exits
    print(
        f"\nDone. Download results:\n"
        f"  modal volume get w101-rl-checkpoints checkpoints/ rl/checkpoints/ --force\n"
        f"  modal volume get w101-rl-checkpoints logs/ rl/logs/ --force"
    )


# ── Web endpoint (deployed app — survives closing your laptop) ────────────────

@app.function(
    image=image,
    timeout=30,
)
@modal.fastapi_endpoint(method="POST")
def start_training(body: dict = {}):
    """Fire-and-forget training trigger for the deployed app.

    Deploy once:  modal deploy rl/modal_train.py
    Then trigger: python rl/modal_train.py --school Fire
                  curl -X POST <url> -H 'Content-Type: application/json' \\
                       -d '{"school":"Fire","n_iterations":300}'
    """
    call = train_remote.spawn(
        school           = body.get("school", "Fire"),
        resume           = body.get("resume", None),
        reset_optimizers = bool(body.get("reset_optimizers", False)),
        reset_volume     = bool(body.get("reset_volume", False)),
        opponents        = body.get("opponents", ""),
        bc_coef          = float(body.get("bc_coef", 0.5)),
        use_evo_deck     = bool(body.get("use_evo_deck", False)),
        evo_seed         = body.get("evo_seed", "moderate"),
        n_iterations     = int(body.get("n_iterations", 200)),
        max_turns        = int(body.get("max_turns", 100)),
        log              = body.get("log", ""),
        forced_cards         = body.get("forced_cards", ""),
        pin_deck             = bool(body.get("pin_deck", False)),
        phase1_wr_threshold  = float(body.get("phase1_wr_threshold", 0.0)),
        phase2_wr_threshold  = float(body.get("phase2_wr_threshold", 0.0)),
        n_curriculum_phases  = int(body.get("n_curriculum_phases", 1)),
        evo_gen_games        = int(body.get("evo_gen_games", 240)),
    )
    return {"status": "started", "call_id": call.object_id, "school": body.get("school", "Fire")}


# ── Local entrypoint (kept for --reset-volume and dev use only) ───────────────
# NOTE: `modal run` ties training to your local process — closing your terminal
# will cancel the job. For real async training use: python rl/modal_train.py

@app.local_entrypoint()
def main(
    school:           str   = "Fire",
    resume:           str   = "",
    reset_optimizers: bool  = False,
    reset_volume:     bool  = False,
    opponents:        str   = "",
    bc_coef:          float = 0.5,
    use_evo_deck:     bool  = False,
    evo_seed:         str   = "moderate",
    iterations:       int   = 200,
    max_turns:        int   = 100,
    log:              str   = "",
    forced_cards:         str   = "",
    pin_deck:             bool  = False,
    phase1_wr_threshold:  float = 0.0,
    phase2_wr_threshold:  float = 0.0,
    n_curriculum_phases:  int   = 1,
):
    """modal run entrypoint — only use for --reset-volume or debugging."""
    train_remote.remote(
        school               = school,
        resume               = resume or None,
        reset_optimizers     = reset_optimizers,
        reset_volume         = reset_volume,
        opponents            = opponents,
        bc_coef              = bc_coef,
        use_evo_deck         = use_evo_deck,
        evo_seed             = evo_seed,
        n_iterations         = iterations,
        max_turns            = max_turns,
        log                  = log,
        forced_cards         = forced_cards,
        pin_deck             = pin_deck,
        phase1_wr_threshold  = phase1_wr_threshold,
        phase2_wr_threshold  = phase2_wr_threshold,
        n_curriculum_phases  = n_curriculum_phases,
    )


# ── CLI trigger (calls the deployed web endpoint) ─────────────────────────────
# Run `python rl/modal_train.py --school Fire` to fire off training
# without Modal's ephemeral app lifecycle killing the job.
# Requires the app to be deployed first: modal deploy rl/modal_train.py

if __name__ == "__main__":
    import argparse
    import json
    import urllib.request

    parser = argparse.ArgumentParser(description="Trigger deployed Modal training job")
    parser.add_argument("--school",           default="Fire")
    parser.add_argument("--resume",           default="")
    parser.add_argument("--reset-optimizers", action="store_true")
    parser.add_argument("--reset-volume",     action="store_true")
    parser.add_argument("--opponents",        default="")
    parser.add_argument("--bc-coef",          type=float, default=0.5)
    parser.add_argument("--use-evo-deck",     action="store_true")
    parser.add_argument("--evo-seed",         default="moderate")
    parser.add_argument("--iterations",       type=int, default=200)
    parser.add_argument("--max-turns",        type=int, default=100)
    parser.add_argument("--log",              default="")
    parser.add_argument("--forced-cards",        default="")
    parser.add_argument("--pin-deck",            action="store_true",
                        help="Phase 1: fix deck to evo-seed, train PPO until phase2-wr-threshold")
    parser.add_argument("--phase1-wr-threshold",  type=float, default=0.0,
                        help="Smoothed WR to advance between phase-1 sub-phases (0 → use phase2 threshold)")
    parser.add_argument("--phase2-wr-threshold",  type=float, default=0.0,
                        help="Smoothed WR to enter phase 2 from the final sub-phase (0 = disabled)")
    parser.add_argument("--n-curriculum-phases",  type=int,   default=1,
                        help="Number of phase-1 sub-phases; enemy level = subphase*100/n (default 1)")
    parser.add_argument("--evo-gen-games",        type=int,   default=240,
                        help="Games per evo generation across the population (default 240)")
    args = parser.parse_args()

    # Resolve the deployed endpoint URL via the Modal client
    try:
        fn  = modal.Function.from_name("w101-rl-training", "start_training")
        url = fn.get_web_url()
    except Exception:
        url = None
    if not url:
        print("ERROR: App not deployed yet (or endpoint URL unavailable).")
        print("Run this first:  modal deploy rl/modal_train.py")
        sys.exit(1)

    payload = {
        "school":           args.school,
        "resume":           args.resume or None,
        "reset_optimizers": args.reset_optimizers,
        "reset_volume":     args.reset_volume,
        "opponents":        args.opponents,
        "bc_coef":          args.bc_coef,
        "use_evo_deck":     args.use_evo_deck,
        "evo_seed":         args.evo_seed,
        "n_iterations":     args.iterations,
        "max_turns":        args.max_turns,
        "log":              args.log,
        "forced_cards":         args.forced_cards,
        "pin_deck":             args.pin_deck,
        "phase1_wr_threshold":  args.phase1_wr_threshold,
        "phase2_wr_threshold":  args.phase2_wr_threshold,
        "n_curriculum_phases":  args.n_curriculum_phases,
        "evo_gen_games":        args.evo_gen_games,
    }
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    print(f"Training started for school: {result['school']}")
    print(f"Call ID: {result['call_id']}")
    print(f"Safe to close your terminal — job runs on Modal.")
    print(f"\nMonitor:  modal app logs w101-rl-training")
    print(f"Download when done:")
    print(f"  modal volume get w101-rl-checkpoints checkpoints/ rl/checkpoints/ --force")
    print(f"  modal volume get w101-rl-checkpoints logs/ rl/logs/ --force")
