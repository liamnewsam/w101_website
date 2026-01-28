from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
import bcrypt, uuid, time
from datetime import datetime, timedelta
import json
import random
import os
#-------------------
from database import SessionLocal
from models import User, GuestSession, PlayerState
from jwt_utils import create_jwt
from config import GUEST_SESSION_LIFETIME
from Deck import simple_life
from config import CHARACTER_IMAGE_PATH
from utils import getRandomPlayerImage
auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["POST"])
def login():
    print("User Logging In")
    data = request.json
    username = data["username"]
    password = data["password"].encode()

    db = SessionLocal()
    user = db.query(User).filter_by(username=username).first()

    if not user:
        return jsonify({"error": "Invalid username/password"}), 400

    if not bcrypt.checkpw(password, user.password_hash.encode()):
        return jsonify({"error": "Invalid username/password"}), 400

    token = create_jwt({"user_id": user.id, "type": "registered"})
    return jsonify({"token": token})


@auth.route("/guest", methods=["POST"])
def guest_login():
    print("Guest Logging In")
    guest_id = uuid.uuid4().hex
    print("generated guest_id:", guest_id)

    expires = datetime.utcnow() + timedelta(seconds=GUEST_SESSION_LIFETIME)

    db = SessionLocal()
    sess = GuestSession(
        guest_id=guest_id,
        expire_at=expires
    )
    db.add(sess)
    db.commit()



    player = PlayerState(
        player_id=guest_id,
        is_guest=True,

        name=f"Guest {guest_id}",
        school="Life",
        deck=json.dumps(simple_life().to_dict()),
        image_path=getRandomPlayerImage()
    )
    db.add(player)
    db.commit()
    
    token = create_jwt({"guest_id": guest_id, "type": "guest"})
    print(f"our token is: {token}")
    return jsonify({"token": token})


@auth.route("/logout", methods=["POST"])
def logout():
    print("Guess logging out")
    # The frontend must delete the stored JWT.
    return jsonify({"success": True})