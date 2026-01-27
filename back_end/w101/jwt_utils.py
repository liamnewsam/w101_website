import jwt
import time
#-------------
from w101.config import SECRET_KEY, JWT_EXPIRY_SECONDS

def create_jwt(payload):
    payload["exp"] = int(time.time()) + JWT_EXPIRY_SECONDS
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_jwt(token):
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
