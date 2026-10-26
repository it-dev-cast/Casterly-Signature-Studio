from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import conflict, not_found
from app.database.models import AuditAction, SignatureTemplate, User
from app.schemas.template import TemplateCreate, TemplateUpdate
from app.services import audit_service


def list_templates(db: Session) -> list[SignatureTemplate]:
    return list(
        db.scalars(select(SignatureTemplate).order_by(SignatureTemplate.is_active.desc(), SignatureTemplate.name)).all()
    )


def count_templates(db: Session) -> int:
    return db.scalar(select(func.count(SignatureTemplate.id))) or 0


def get_template(db: Session, template_id: int) -> SignatureTemplate:
    template = db.get(SignatureTemplate, template_id)
    if template is None:
        raise not_found("Signature template")
    return template


def get_active_template(db: Session) -> SignatureTemplate | None:
    return db.scalar(select(SignatureTemplate).where(SignatureTemplate.is_active.is_(True)))


def _ensure_unique_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    stmt = select(SignatureTemplate.id).where(func.lower(SignatureTemplate.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(SignatureTemplate.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise conflict("DUPLICATE_TEMPLATE", f"A template named '{name}' already exists.")


def create_template(db: Session, data: TemplateCreate, actor: User) -> SignatureTemplate:
    _ensure_unique_name(db, data.name)
    # The very first template becomes active so signatures always have a design.
    template = SignatureTemplate(**data.model_dump(), is_active=get_active_template(db) is None)
    db.add(template)
    db.flush()
    audit_service.record(
        db, AuditAction.TEMPLATE_CREATED, user_id=actor.id, entity_type="template",
        entity_id=template.id, description=f"Created template '{template.name}'",
    )
    db.commit()
    db.refresh(template)
    return template


def update_template(db: Session, template_id: int, data: TemplateUpdate, actor: User) -> SignatureTemplate:
    template = get_template(db, template_id)
    _ensure_unique_name(db, data.name, exclude_id=template.id)
    for name, value in data.model_dump().items():
        setattr(template, name, value)
    audit_service.record(
        db, AuditAction.TEMPLATE_UPDATED, user_id=actor.id, entity_type="template",
        entity_id=template.id, description=f"Updated template '{template.name}'",
    )
    db.commit()
    db.refresh(template)
    return template


def activate_template(db: Session, template_id: int, actor: User) -> SignatureTemplate:
    template = get_template(db, template_id)
    if template.is_active:
        return template
    db.execute(update(SignatureTemplate).where(SignatureTemplate.is_active.is_(True)).values(is_active=False))
    db.flush()
    template.is_active = True
    audit_service.record(
        db, AuditAction.TEMPLATE_ACTIVATED, user_id=actor.id, entity_type="template",
        entity_id=template.id, description=f"Activated template '{template.name}'",
    )
    db.commit()
    db.refresh(template)
    return template
