"""Password hashing (Argon2) and JWT helpers."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()
# Verifying against a dummy hash keeps login timing similar whether or not the account exists.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing-only")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        matched = _hasher.verify(password_hash or _DUMMY_HASH, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return matched and password_hash is not None


def create_access_token(user_id: int, role: str, remember_me: bool = False) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if remember_me:
        expires = now + timedelta(days=settings.remember_me_expire_days)
    else:
        expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    jti = uuid.uuid4().hex
    payload = {"sub": str(user_id), "role": role, "jti": jti, "iat": now, "exp": expires}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires


def decode_access_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError on failure."""
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "exp", "jti"]},
    )
