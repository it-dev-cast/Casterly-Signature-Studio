from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database.database import get_db
from app.database.models import User
from app.schemas.common import ApiResponse, Page, ok
from app.schemas.misc import AuditLogRead
from app.services import audit_service

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=ApiResponse[Page[AuditLogRead]])
def list_audit_logs(
    action: str | None = Query(default=None, max_length=40),
    entity_type: str | None = Query(default=None, max_length=40),
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    items, total = audit_service.list_logs(
        db, page=page, page_size=page_size, action=action, entity_type=entity_type, q=q
    )
    return ok(
        {"items": [audit_service.to_read(i) for i in items], "total": total, "page": page, "page_size": page_size}
    )
