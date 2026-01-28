

import os

SECRET_KEY = os.environ.get("SECRET_KEY", "devsecret123")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///game.db")
JWT_EXPIRY_SECONDS = 60 * 60 * 2  # 24 hours
GUEST_SESSION_LIFETIME = 60 * 60  # 1 hour


ESCAPE = "q"

HIDDEN_KEYS = [ESCAPE]

CHARACTER_IMAGE_PATH = "static/w101/icons/characters/"