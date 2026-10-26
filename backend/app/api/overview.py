from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database.database import get_db
from app.database.models import Banner, BannerStatus, Employee, User
from app.schemas.common import ApiResponse, ok
from app.schemas.misc import OverviewRead
from app.services import banner_service, template_service

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=ApiResponse[OverviewRead])
def overview(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    total, active = db.execute(
        select(func.count(Employee.id), func.count(Employee.id).filter(Employee.is_active.is_(True)))
    ).one()
    drafts = db.scalar(select(func.count(Banner.id)).where(Banner.status == BannerStatus.DRAFT)) or 0
    current = banner_service.get_current_published_banner(db)
    return ok(
        {
            "stats": {
                "total_employees": total,
                "active_employees": active,
                "draft_banners": drafts,
                "signature_templates": template_service.count_templates(db),
                "has_published_banner": current is not None,
            },
            "current_banner": banner_service.to_read(current, current.id, with_html=True) if current else None,
            "active_template": template_service.get_active_template(db),
        }
    )
