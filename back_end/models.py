from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
#----------------
from database import Base

SCHOOLS_LIST = ["fire", "ice", "storm", "life", "death", "myth", "balance"]

# ELO-to-level mapping — kept in sync with frontend levelUtils.js
_ELO_FLOOR       = 100   # starting / minimum ELO for each school
_ELO_PER_LEVEL   = 32    # ~1 win vs same-level opponent (K=64, expected≈0.5) = ~1 level
_SCHOOL_LEVEL_MIN = 10
_SCHOOL_LEVEL_MAX = 170


def _elo_to_level(elo: int) -> int:
    return max(_SCHOOL_LEVEL_MIN, min(_SCHOOL_LEVEL_MAX, (elo - _ELO_FLOOR) // _ELO_PER_LEVEL + _SCHOOL_LEVEL_MIN))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class PlayerState(Base):
    __tablename__ = "player_state"

    player_id = Column(String, primary_key=True)  # can be user.id or guest_id
    is_guest = Column(Boolean, default=False)

    name = Column(String)
    school = Column(String)

    # Legacy single-deck field — kept for rows not yet migrated
    deck = Column(JSON)

    # Multi-deck support
    decks = Column(JSON, default=list)
    selected_deck_index = Column(Integer, default=0)

    # Overall match history (display only)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    # Per-school win/loss counts (display only — level is driven by school_elos)
    school_wins   = Column(JSON, default=dict)
    school_losses = Column(JSON, default=dict)

    # Per-school ELO — drives per-school level
    school_elos = Column(JSON, default=dict)

    # Legacy global ELO (kept for backward compat; matchmaking now uses school_elos)
    elo = Column(Integer, default=100)

    image_path = Column(String)

    def _school_elo(self, school: str) -> int:
        """Return the ELO for a specific school, defaulting to the floor."""
        return (self.school_elos or {}).get(school.lower(), _ELO_FLOOR)

    def _compute_school_level(self, school: str) -> int:
        """Return the display level for a specific school."""
        return _elo_to_level(self._school_elo(school))

    def _compute_level(self):
        """Return the level for the player's currently active school."""
        return self._compute_school_level(self.school or "balance")

    def _selected_deck(self):
        """Return the currently selected deck dict (falls back to legacy deck field)."""
        decks = self.decks or []
        if decks:
            idx = min(self.selected_deck_index or 0, len(decks) - 1)
            return decks[idx]
        return self.deck  # legacy fallback

    def to_dict(self):
        wins = self.wins or 0
        losses = self.losses or 0
        decks = self.decks or []
        school_levels = {s: self._compute_school_level(s) for s in SCHOOLS_LIST}
        school_elos = {s: self._school_elo(s) for s in SCHOOLS_LIST}
        return {
            "name": self.name,
            "school": self.school,
            "deck": self._selected_deck(),
            "decks": decks,
            "selected_deck_index": self.selected_deck_index or 0,
            "user_id": self.player_id,
            "image_path": self.image_path,
            "wins": wins,
            "losses": losses,
            "elo": self.elo or _ELO_FLOOR,
            "level": self._compute_level(),
            "school_levels": school_levels,
            "school_elos": school_elos,
            "school_wins":   dict(self.school_wins   or {}),
            "school_losses": dict(self.school_losses or {}),
        }


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    guest_id = Column(String, primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    expire_at = Column(DateTime)


class GameLog(Base):
    __tablename__ = "game_logs"

    game_id = Column(String, primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    winner = Column(String)           # "A" or "B"
    player_ids = Column(JSON)         # list of human player ID strings
    players = Column(JSON)            # match result player data (for display)
    initial_game_state = Column(JSON) # public game state before any turns
    turns = Column(JSON)              # [{log: [...], finalGameState: {...}}] per turn
