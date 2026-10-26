"""Signature endpoints.

`GET /api/signatures/{employee_id}/html` returns a raw, email-ready HTML fragment
(text/html). It is the endpoint a future Outlook add-in or Gmail sync job calls.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.errors import AppError
from app.database.database import get_db
from app.database.models import User, UserRole
from app.schemas.common import ApiResponse, ok
from app.schemas.misc import SignatureRead
from app.services import banner_service, employee_service, signature_service
from app.services.signature_service import SignatureResult

router = APIRouter(prefix="/signatures", tags=["signatures"])


def _authorize(db: Session, user: User, employee_id: int) -> None:
    if user.role == UserRole.ADMIN:
        return
    own = employee_service.get_employee_for_user(db, user)
    if own.id != employee_id:
        raise AppError(403, "FORBIDDEN", "You can only access your own signature.")


def _generate(db: Session, user: User, employee_id: int, template_id: int | None) -> SignatureResult:
    _authorize(db, user, employee_id)
    # Only admins may preview with a non-active template.
    tid = template_id if user.role == UserRole.ADMIN else None
    return signature_service.generate_employee_signature(db, employee_id, tid)


def _to_read(result: SignatureResult) -> dict:
    banner = result.banner
    return {
        "employee": result.employee,
        "template": result.template,
        "banner": banner_service.to_read(banner, banner.id, with_html=True) if banner else None,
        "html": result.html,
        "live_html": result.live_html,
        "generated_at": result.generated_at,
    }


@router.get("/me", response_model=ApiResponse[SignatureRead])
def my_signature(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee = employee_service.get_employee_for_user(db, user)
    return ok(_to_read(signature_service.generate_employee_signature(db, employee.id)))


@router.get("/{employee_id}", response_model=ApiResponse[SignatureRead])
def get_signature(
    employee_id: int,
    template_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ok(_to_read(_generate(db, user, employee_id, template_id)))


@router.get("/{employee_id}/preview", response_class=HTMLResponse)
def preview_signature(
    employee_id: int,
    template_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = _generate(db, user, employee_id, template_id)
    return HTMLResponse(signature_service.wrap_document(result.html, f"{result.employee.full_name} - Signature"))


@router.get("/{employee_id}/html", response_class=HTMLResponse)
def signature_html(
    employee_id: int,
    template_id: int | None = Query(default=None),
    download: bool = False,
    live: bool = Query(default=False, description="Use the live banner addresses (for pasting into Outlook)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = _generate(db, user, employee_id, template_id)
    html = result.live_html if live else result.html
    headers = {"Cache-Control": "no-store"}
    if download:
        filename = f"signature-{result.employee.employee_code.lower()}.html"
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        content = signature_service.wrap_document(html, f"{result.employee.full_name} - Signature")
        return HTMLResponse(content, headers=headers)
    return HTMLResponse(html, headers=headers)
