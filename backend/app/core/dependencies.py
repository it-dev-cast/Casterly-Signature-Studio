"""FastAPI dependencies for authentication and role-based authorization."""
from dataclasses import dataclass
from datetime import datetime, timezone

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.database.database import get_db
from app.database.models import User, UserRole
from app.services import auth_service

_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    jti: str
    expires_at: datetime


def get_auth_context(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> AuthContext:
    if creds is None or not creds.credentials:
        raise AppError(401, "NOT_AUTHENTICATED", "Please sign in to continue.")
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise AppError(401, "TOKEN_EXPIRED", "Your session has expired. Please login again.") from None
    except jwt.InvalidTokenError:
        raise AppError(401, "INVALID_TOKEN", "Your session is invalid. Please login again.") from None

    if auth_service.is_revoked(db, payload["jti"]):
        raise AppError(401, "TOKEN_REVOKED", "Your session has ended. Please login again.")
    try:
        user = db.get(User, int(payload["sub"]))
    except (TypeError, ValueError):
        user = None
    if user is None:
        raise AppError(401, "INVALID_TOKEN", "Your session is invalid. Please login again.")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_DISABLED", "Your account has been deactivated.")
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    return AuthContext(user=user, jti=payload["jti"], expires_at=expires_at)


def get_current_user(ctx: AuthContext = Depends(get_auth_context)) -> User:
    return ctx.user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise AppError(403, "FORBIDDEN", "You do not have permission to perform this action.")
    return user
