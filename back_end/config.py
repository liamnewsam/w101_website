

import os

from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set")

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///game.db")
JWT_EXPIRY_SECONDS = 60 * 60 * 2  # 2 hours
GUEST_SESSION_LIFETIME = 60 * 60  # 1 hour


ESCAPE = "q"

HIDDEN_KEYS = [ESCAPE]

CHARACTER_IMAGE_PATH = "static/w101/icons/characters/"