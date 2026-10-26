from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import create_access_token, verify_password
from app.database.models import AuditAction, RevokedToken, User
from app.database.types import utcnow
from app.services import audit_service


def authenticate(db: Session, email: str, password: str, remember_me: bool) -> tuple[User, str, datetime]:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    # verify_password runs even when the user is missing to avoid timing-based user enumeration.
    if not verify_password(password, user.password_hash if user else None) or user is None:
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password.")
    if not user.is_active or (user.employee is not None and not user.employee.is_active):
        raise AppError(403, "ACCOUNT_DISABLED", "Your account has been deactivated. Contact your administrator.")

    token, _, expires = create_access_token(user.id, user.role.value, remember_me)
    audit_service.record(
        db, AuditAction.LOGIN, user_id=user.id, entity_type="user", entity_id=user.id,
        description=f"{user.email} signed in",
    )
    db.commit()
    return user, token, expires


def logout(db: Session, user: User, jti: str, expires_at: datetime) -> None:
    # Housekeeping: drop deny-list entries for tokens that have expired anyway.
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < utcnow()))
    if db.get(RevokedToken, jti) is None:
        db.add(RevokedToken(jti=jti, expires_at=expires_at))
    audit_service.record(
        db, AuditAction.LOGOUT, user_id=user.id, entity_type="user", entity_id=user.id,
        description=f"{user.email} signed out",
    )
    db.commit()


def is_revoked(db: Session, jti: str) -> bool:
    return db.get(RevokedToken, jti) is not None
