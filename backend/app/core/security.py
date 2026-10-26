import hashlib
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

ph = PasswordHasher()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False

def get_password_hash(password: str) -> str:
    return ph.hash(password)

def create_access_token(subject: str, org_id: str = None, role: str = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    if org_id:
        to_encode["org_id"] = str(org_id)
    if role:
        to_encode["role"] = str(role)
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_ACCESS_SECRET, algorithm="HS256")
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=["HS256"])
        return decoded_token
    except jwt.PyJWTError:
        return None

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256((token + settings.JWT_REFRESH_PEPPER).encode()).hexdigest()
