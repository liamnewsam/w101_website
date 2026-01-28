from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
import json
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
    deck = Column(JSON)

    image_path = Column(String)

    def to_dict(self):
        return {
            "name": self.name,
            "school": self.school,
            "deck": json.loads(self.deck),
            "user_id": self.player_id,
            "image_path": self.image_path
        }


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    guest_id = Column(String, primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    expire_at = Column(DateTime)
