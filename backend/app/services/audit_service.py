from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.database.models import AuditAction, AuditLog


def record(
    db: Session,
    action: AuditAction,
    *,
    user_id: int | None,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    description: str | None = None,
) -> AuditLog:
    """Add an audit entry to the current transaction (the caller commits)."""
    log = AuditLog(
        user_id=user_id,
        action=action.value,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        description=description,
    )
    db.add(log)
    return log


def list_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    action: str | None = None,
    entity_type: str | None = None,
    q: str | None = None,
) -> tuple[list[AuditLog], int]:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if q:
        stmt = stmt.where(or_(AuditLog.description.ilike(f"%{q}%"), AuditLog.action.ilike(f"%{q}%")))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.options(joinedload(AuditLog.user))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total


def to_read(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "user_email": log.user.email if log.user else None,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "description": log.description,
        "created_at": log.created_at,
    }
