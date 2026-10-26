from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database.database import get_db
from app.database.models import User
from app.renderers import LAYOUTS
from app.schemas.common import ApiResponse, ok
from app.schemas.template import LayoutInfo, TemplateCreate, TemplateRead, TemplateUpdate
from app.services import template_service

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=ApiResponse[list[TemplateRead]])
def list_templates(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return ok(template_service.list_templates(db))


@router.get("/layouts", response_model=ApiResponse[list[LayoutInfo]])
def list_layouts(_: User = Depends(require_admin)):
    return ok([{"key": l.key, "name": l.name, "description": l.description} for l in LAYOUTS.values()])


@router.post("", response_model=ApiResponse[TemplateRead], status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return ok(template_service.create_template(db, body, admin))


@router.put("/{template_id}", response_model=ApiResponse[TemplateRead])
def update_template(
    template_id: int, body: TemplateUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    return ok(template_service.update_template(db, template_id, body, admin))


@router.post("/{template_id}/activate", response_model=ApiResponse[TemplateRead])
def activate_template(template_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return ok(template_service.activate_template(db, template_id, admin))
