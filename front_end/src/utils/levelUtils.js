// Kept in sync with backend models.py constants
export const ELO_FLOOR     = 100;
export const ELO_PER_LEVEL = 32;   // K=64, same-level win ≈ +32 ELO ≈ +1 level
export const LEVEL_MIN     = 10;
export const LEVEL_MAX     = 170;

export function computeLevel(elo) {
  return Math.max(LEVEL_MIN, Math.min(LEVEL_MAX, Math.floor((elo - ELO_FLOOR) / ELO_PER_LEVEL) + LEVEL_MIN));
}

// Returns [0, 1) representing progress within the current level.
export function computeLevelProgress(elo) {
  const level = computeLevel(elo);
  if (level >= LEVEL_MAX) return 1;
  const levelFloorElo = ELO_FLOOR + (level - LEVEL_MIN) * ELO_PER_LEVEL;
  return Math.max(0, Math.min(1, (elo - levelFloorElo) / ELO_PER_LEVEL));
}
