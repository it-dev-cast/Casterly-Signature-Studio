from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin
from app.database.database import get_db
from app.database.models import BannerStatus, User
from app.schemas.banner import (
    BannerCreate,
    BannerHtml,
    BannerPreviewRequest,
    BannerRead,
    BannerUpdate,
    BannerWithHtml,
    CurrentBanner,
)
from app.schemas.common import ApiResponse, ok
from app.services import banner_service

router = APIRouter(prefix="/banners", tags=["banners"])


def _detail(db: Session, banner) -> dict:
    return ok(banner_service.to_read(banner, banner_service.current_id(db), with_html=True))


@router.get("", response_model=ApiResponse[list[BannerRead]])
def list_banners(
    status: BannerStatus | None = None,
    q: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    current = banner_service.current_id(db)
    return ok([banner_service.to_read(b, current) for b in banner_service.list_banners(db, status, q)])


@router.get("/current", response_model=ApiResponse[CurrentBanner])
def current_banner(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """The banner currently included in signatures. Readable by every signed-in user."""
    banner = banner_service.get_current_published_banner(db)
    data = banner_service.to_read(banner, banner.id, with_html=True) if banner else None
    return ok({"banner": data})


@router.post("/preview", response_model=ApiResponse[BannerHtml])
def preview_unsaved(body: BannerPreviewRequest, _: User = Depends(require_admin)):
    return ok({"html": banner_service.banner_html(body)})


@router.post("", response_model=ApiResponse[BannerWithHtml], status_code=status.HTTP_201_CREATED)
def create_banner(body: BannerCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return _detail(db, banner_service.create_banner(db, body, admin))


@router.get("/{banner_id}", response_model=ApiResponse[BannerWithHtml])
def get_banner(banner_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return _detail(db, banner_service.get_banner(db, banner_id))


@router.put("/{banner_id}", response_model=ApiResponse[BannerWithHtml])
def update_banner(
    banner_id: int, body: BannerUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    return _detail(db, banner_service.update_banner(db, banner_id, body, admin))


@router.post("/{banner_id}/publish", response_model=ApiResponse[BannerWithHtml])
def publish(banner_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return _detail(db, banner_service.publish_banner(db, banner_id, admin))


@router.post("/{banner_id}/unpublish", response_model=ApiResponse[BannerWithHtml])
def unpublish(banner_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return _detail(db, banner_service.unpublish_banner(db, banner_id, admin))


@router.post("/{banner_id}/archive", response_model=ApiResponse[BannerWithHtml])
def archive(banner_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return _detail(db, banner_service.archive_banner(db, banner_id, admin))


@router.delete("/{banner_id}", response_model=ApiResponse[dict])
def delete(banner_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    banner_service.delete_banner(db, banner_id, admin)
    return ok({"deleted": True})
