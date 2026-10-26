"""Banner lifecycle and THE single source of truth for the current company banner."""
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request, conflict, not_found
from app.database.models import AuditAction, Banner, BannerStatus, User
from app.database.types import utcnow
from app.renderers.banner import render_banner_html
from app.renderers.context import BannerView
from app.schemas.banner import BannerCreate, BannerFields, BannerUpdate
from app.services import audit_service
from app.utils.urls import resolve_public_url


# --------------------------------------------------------------------------- #
# Current banner - the ONLY place that decides which banner is in signatures. #
# --------------------------------------------------------------------------- #
def get_current_published_banner(db: Session, now: datetime | None = None) -> Banner | None:
    """The banner that belongs in every signature right now, or None.

    A banner is current when it is PUBLISHED and `now` falls inside its optional
    start/end window. Uses the (status) index; at most one PUBLISHED row exists.
    """
    now = now or utcnow()
    return db.scalar(
        select(Banner).where(
            Banner.status == BannerStatus.PUBLISHED,
            or_(Banner.start_date.is_(None), Banner.start_date <= now),
            or_(Banner.end_date.is_(None), Banner.end_date > now),
        )
    )


def effective_status(banner: Banner, now: datetime | None = None) -> BannerStatus:
    """Derive SCHEDULED / EXPIRED for a PUBLISHED banner from its date window."""
    if banner.status != BannerStatus.PUBLISHED:
        return banner.status
    now = now or utcnow()
    if banner.start_date and banner.start_date > now:
        return BannerStatus.SCHEDULED
    if banner.end_date and banner.end_date <= now:
        return BannerStatus.EXPIRED
    return BannerStatus.PUBLISHED


# ------------------------------ rendering --------------------------------- #
def banner_view(banner: Banner | BannerFields) -> BannerView:
    return BannerView(
        title=banner.title,
        image_src=resolve_public_url(banner.image_url) or "",
        target_url=banner.target_url,
    )


def banner_html(banner: Banner | BannerFields) -> str:
    return render_banner_html(banner_view(banner))


def to_read(banner: Banner, current_id: int | None, *, with_html: bool = False) -> dict:
    data = {
        "id": banner.id,
        "name": banner.name,
        "title": banner.title,
        "description": banner.description,
        "image_url": banner.image_url,
        "image_public_url": resolve_public_url(banner.image_url) or "",
        "target_url": banner.target_url,
        "status": banner.status,
        "effective_status": effective_status(banner),
        "is_current": banner.id == current_id,
        "start_date": banner.start_date,
        "end_date": banner.end_date,
        "published_at": banner.published_at,
        "created_by": banner.created_by,
        "created_by_email": banner.creator.email if banner.creator else None,
        "created_at": banner.created_at,
        "updated_at": banner.updated_at,
    }
    if with_html:
        data["html"] = banner_html(banner)
    return data


def current_id(db: Session) -> int | None:
    current = get_current_published_banner(db)
    return current.id if current else None


# -------------------------------- queries --------------------------------- #
def list_banners(db: Session, status: BannerStatus | None = None, q: str | None = None) -> list[Banner]:
    stmt = select(Banner)
    if status in (BannerStatus.DRAFT, BannerStatus.ARCHIVED):
        stmt = stmt.where(Banner.status == status)
    elif status is not None:
        stmt = stmt.where(Banner.status == BannerStatus.PUBLISHED)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Banner.name.ilike(like), Banner.title.ilike(like)))
    banners = list(db.scalars(stmt.order_by(Banner.created_at.desc(), Banner.id.desc())).unique().all())
    if status in (BannerStatus.PUBLISHED, BannerStatus.SCHEDULED, BannerStatus.EXPIRED):
        banners = [b for b in banners if effective_status(b) == status]
    return banners


def get_banner(db: Session, banner_id: int, *, for_update: bool = False) -> Banner:
    stmt = select(Banner).where(Banner.id == banner_id)
    if for_update:
        stmt = stmt.with_for_update(of=Banner)
    banner = db.scalar(stmt)
    if banner is None:
        raise not_found("Banner")
    return banner


def get_published_row(db: Session) -> Banner | None:
    """The row holding PUBLISHED status (it may be scheduled or expired)."""
    return db.scalar(select(Banner).where(Banner.status == BannerStatus.PUBLISHED))


# ------------------------------- mutations -------------------------------- #
def create_banner(db: Session, data: BannerCreate, actor: User) -> Banner:
    banner = Banner(**data.model_dump(), status=BannerStatus.DRAFT, created_by=actor.id)
    db.add(banner)
    db.flush()
    audit_service.record(
        db, AuditAction.BANNER_CREATED, user_id=actor.id, entity_type="banner",
        entity_id=banner.id, description=f"Created banner '{banner.name}' as draft",
    )
    db.commit()
    db.refresh(banner)
    return banner


def update_banner(db: Session, banner_id: int, data: BannerUpdate, actor: User) -> Banner:
    banner = get_banner(db, banner_id)
    if banner.status == BannerStatus.ARCHIVED:
        raise conflict("BANNER_ARCHIVED", "Archived banners cannot be edited.")
    for name, value in data.model_dump().items():
        setattr(banner, name, value)
    audit_service.record(
        db, AuditAction.BANNER_UPDATED, user_id=actor.id, entity_type="banner",
        entity_id=banner.id, description=f"Updated banner '{banner.name}'",
    )
    db.commit()
    db.refresh(banner)
    return banner


def publish_banner(db: Session, banner_id: int, actor: User) -> Banner:
    """Atomically make `banner_id` the one PUBLISHED banner."""
    try:
        banner = get_banner(db, banner_id, for_update=True)
        if banner.status == BannerStatus.ARCHIVED:
            raise conflict("BANNER_ARCHIVED", "Archived banners cannot be published.")
        if banner.status == BannerStatus.PUBLISHED:
            raise conflict("ALREADY_PUBLISHED", "This banner is already published.")

        # 1. Validate the stored banner with the same rules used on create/update.
        try:
            BannerFields.model_validate(banner, from_attributes=True)
        except ValueError:
            raise bad_request("INVALID_BANNER", "This banner is incomplete or invalid. Edit it before publishing.") from None
        now = utcnow()
        if banner.end_date and banner.end_date <= now:
            raise bad_request("BANNER_EXPIRED", "This banner's end date has already passed.")

        # 2-3. Demote the currently published banner (kept as a draft for history).
        previous = db.scalar(
            select(Banner).where(Banner.status == BannerStatus.PUBLISHED).with_for_update(of=Banner)
        )
        if previous is not None:
            previous.status = BannerStatus.DRAFT
            db.flush()  # free the single-published unique index before promoting
            audit_service.record(
                db, AuditAction.BANNER_UNPUBLISHED, user_id=actor.id, entity_type="banner",
                entity_id=previous.id, description=f"Unpublished '{previous.name}' (replaced by '{banner.name}')",
            )

        # 4-6. Publish, stamp and audit.
        banner.status = BannerStatus.PUBLISHED
        banner.published_at = now
        audit_service.record(
            db, AuditAction.BANNER_PUBLISHED, user_id=actor.id, entity_type="banner",
            entity_id=banner.id, description=f"Published banner '{banner.name}'",
        )
        db.commit()  # 7.
    except IntegrityError:
        db.rollback()
        raise conflict("PUBLISH_CONFLICT", "Another banner was published at the same time. Please try again.") from None
    except AppError:
        db.rollback()
        raise
    db.refresh(banner)
    return banner


def unpublish_banner(db: Session, banner_id: int, actor: User) -> Banner:
    banner = get_banner(db, banner_id)
    if banner.status != BannerStatus.PUBLISHED:
        raise conflict("NOT_PUBLISHED", "Only the published banner can be unpublished.")
    banner.status = BannerStatus.DRAFT
    audit_service.record(
        db, AuditAction.BANNER_UNPUBLISHED, user_id=actor.id, entity_type="banner",
        entity_id=banner.id, description=f"Unpublished banner '{banner.name}'",
    )
    db.commit()
    db.refresh(banner)
    return banner


def archive_banner(db: Session, banner_id: int, actor: User) -> Banner:
    banner = get_banner(db, banner_id)
    if banner.status == BannerStatus.ARCHIVED:
        raise conflict("ALREADY_ARCHIVED", "This banner is already archived.")
    was_published = banner.status == BannerStatus.PUBLISHED
    banner.status = BannerStatus.ARCHIVED  # an archived banner can never be current
    suffix = " (it was published and has been removed from signatures)" if was_published else ""
    audit_service.record(
        db, AuditAction.BANNER_ARCHIVED, user_id=actor.id, entity_type="banner",
        entity_id=banner.id, description=f"Archived banner '{banner.name}'{suffix}",
    )
    db.commit()
    db.refresh(banner)
    return banner


def delete_banner(db: Session, banner_id: int, actor: User) -> None:
    banner = get_banner(db, banner_id)
    if banner.status == BannerStatus.PUBLISHED:
        raise conflict("BANNER_PUBLISHED", "Unpublish this banner before deleting it.")
    name = banner.name
    db.delete(banner)
    audit_service.record(
        db, AuditAction.BANNER_DELETED, user_id=actor.id, entity_type="banner",
        entity_id=banner_id, description=f"Deleted banner '{name}'",
    )
    db.commit()
