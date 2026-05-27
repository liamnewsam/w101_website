from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
#----------------
from database import Base

SCHOOLS_LIST = ["fire", "ice", "storm", "life", "death", "myth", "balance"]
_WINS_PER_LEVEL = 5

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
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

    # Match history
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    # Per-school win counts — drives per-school leveling
    school_wins = Column(JSON, default=dict)

    # Elo rating — used for matchmaking
    elo = Column(Integer, default=100)

    image_path = Column(String)

    def _compute_school_level(self, school: str) -> int:
        """Return the level for a specific school based on wins with that school."""
        sw = (self.school_wins or {}).get(school.lower(), 0)
        return min(100, sw // _WINS_PER_LEVEL + 1)

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
        return {
            "name": self.name,
            "school": self.school,
            "deck": self._selected_deck(),   # for loadPlayer compat
            "decks": decks,
            "selected_deck_index": self.selected_deck_index or 0,
            "user_id": self.player_id,
            "image_path": self.image_path,
            "wins": wins,
            "losses": losses,
            "elo": self.elo or 100,
            "level": self._compute_level(),          # active school's level
            "school_levels": school_levels,           # all seven school levels
        }


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    guest_id = Column(String, primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    expire_at = Column(DateTime)
