from flask import Blueprint, request, jsonify
import bcrypt, uuid
from datetime import datetime, timedelta
#-------------------
from database import SessionLocal
from models import User, GuestSession, PlayerState
from jwt_utils import create_jwt
from config import GUEST_SESSION_LIFETIME
from Deck import simple_life, circular_arrow
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
        token = create_jwt({"user_id": user.id, "type": "registered"})
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
            school="Life",
            deck=simple_life().to_dict(),
            image_path=getRandomPlayerImage()
        ))
        db.commit()
    finally:
        db.close()

    token = create_jwt({"guest_id": guest_id, "type": "guest"})
    return jsonify({"token": token})


@auth.route("/logout", methods=["POST"])
def logout():
    # JWT is stateless; the client must delete its stored token.
    # Tokens remain valid until expiry — add a denylist table here if needed.
    return jsonify({"success": True})
