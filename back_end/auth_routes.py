from flask import Blueprint, request, jsonify
import bcrypt, uuid
from datetime import datetime, timedelta, timezone
#-------------------
from database import SessionLocal
from models import User, GuestSession, PlayerState
from jwt_utils import create_jwt
from config import GUEST_SESSION_LIFETIME
from Deck import *
from utils import getRandomPlayerImage

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400
    password = password.encode()

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user or not bcrypt.checkpw(password, user.password_hash.encode()):
            return jsonify({"error": "Invalid username/password"}), 400
        token = create_jwt({"user_id": str(user.id), "type": "registered"})
        return jsonify({"token": token})
    finally:
        db.close()


@auth.route("/guest", methods=["POST"])
def guest_login():
    guest_id = uuid.uuid4().hex
    expires = datetime.now(timezone.utc) + timedelta(seconds=GUEST_SESSION_LIFETIME)

    decks, school, selected_deck_index = new_player_state()

    db = SessionLocal()
    try:
        db.add(GuestSession(guest_id=guest_id, expire_at=expires))
        db.add(PlayerState(
            player_id=guest_id,
            is_guest=True,
            name=f"Guest {guest_id[:6]}",
            school=school,
            decks=decks,
            selected_deck_index=selected_deck_index,
            wins=0,
            losses=0,
            elo=100,
            image_path=getRandomPlayerImage()
        ))
        db.commit()
    finally:
        db.close()

    token = create_jwt({"guest_id": guest_id, "type": "guest"})
    return jsonify({"token": token})


@auth.route("/register", methods=["POST"])
def register():
    data = request.json
    if not data:
        return jsonify({"error": "Missing request body"}), 400
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    db = SessionLocal()
    try:
        if db.query(User).filter_by(username=username).first():
            return jsonify({"error": "Username already taken"}), 409
        decks, school, selected_deck_index = new_player_state()
        user = User(username=username, password_hash=password_hash)
        db.add(user)
        db.flush()  # populate user.id
        db.add(PlayerState(
            player_id=str(user.id),
            is_guest=False,
            name=username,
            school=school,
            decks=decks,
            selected_deck_index=selected_deck_index,
            wins=0,
            losses=0,
            elo=100,
            image_path=getRandomPlayerImage()
        ))
        db.commit()
        token = create_jwt({"user_id": str(user.id), "type": "registered"})
        return jsonify({"token": token}), 201
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@auth.route("/demo", methods=["POST"])
def demo_login():
    """Create a temporary demo session with no database record."""
    demo_id = "demo_" + uuid.uuid4().hex
    token = create_jwt({"user_id": demo_id, "type": "demo"})
    return jsonify({"token": token, "demo_id": demo_id})


@auth.route("/logout", methods=["POST"])
def logout():
    # JWT is stateless; the client must delete its stored token.
    # Tokens remain valid until expiry — add a denylist table here if needed.
    return jsonify({"success": True})
