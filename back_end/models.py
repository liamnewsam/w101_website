from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
#----------------
from database import Base

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

    # Match history — level is derived from these
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)

    image_path = Column(String)

    def _compute_level(self):
        wins = self.wins or 0
        losses = self.losses or 0
        # 3 wins = 1 level; losses also contribute slightly
        return 1 + wins // 3 + losses // 10

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
            "level": self._compute_level(),
        }


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    guest_id = Column(String, primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    expire_at = Column(DateTime)
