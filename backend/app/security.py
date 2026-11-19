import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from .config import settings


def _now():
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


DUMMY = hash_password("timing-equalizer")  # compared when the email is unknown


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def make_access(sub: str) -> str:
    claims = {"sub": sub, "type": "access", "iat": _now(), "exp": _now() + timedelta(minutes=settings.access_minutes)}
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def make_refresh(sub: str):
    exp = _now() + timedelta(days=settings.refresh_days)
    claims = {"sub": sub, "type": "refresh", "jti": uuid.uuid4().hex, "iat": _now(), "exp": exp}
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm), exp


def decode(token: str, expected: str):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    return payload if payload.get("type") == expected else None
