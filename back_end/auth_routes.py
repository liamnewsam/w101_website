from flask import Blueprint, request, jsonify
import bcrypt, uuid
from datetime import datetime, timedelta
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
    expires = datetime.utcnow() + timedelta(seconds=GUEST_SESSION_LIFETIME)

    db = SessionLocal()
    try:
        db.add(GuestSession(guest_id=guest_id, expire_at=expires))
        db.add(PlayerState(
            player_id=guest_id,
            is_guest=True,
            name=f"Guest {guest_id[:6]}",
            school="Balance",
            decks=[contrived_player_deck().to_dict()],
            selected_deck_index=0,
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
        user = User(username=username, password_hash=password_hash)
        db.add(user)
        db.flush()  # populate user.id
        db.add(PlayerState(
            player_id=str(user.id),
            is_guest=False,
            name=username,
            school="Balance",
            decks=[simple_balance().to_dict()],
            selected_deck_index=0,
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


@auth.route("/logout", methods=["POST"])
def logout():
    # JWT is stateless; the client must delete its stored token.
    # Tokens remain valid until expiry — add a denylist table here if needed.
    return jsonify({"success": True})
