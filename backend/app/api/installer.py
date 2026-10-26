"""Outlook signature installer endpoints (see app/installer.py for how the key works)."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import installer
from app.core.dependencies import get_current_user
from app.core.errors import AppError
from app.database.database import get_db
from app.database.models import AuditAction, Employee, User, UserRole
from app.renderers.html_utils import html_to_text
from app.schemas.common import ok
from app.services import audit_service, employee_service, settings_service, signature_service

router = APIRouter(tags=["installer"])
# No login: used by the installer program and served by the public gateway.
public_router = APIRouter(tags=["installer"])


def _installer_response(db: Session, employee: Employee, actor: User) -> FileResponse:
    if not installer.INSTALLER_FILE.is_file():
        raise AppError(503, "INSTALLER_UNAVAILABLE", "The Outlook installer has not been built on this server yet.")
    audit_service.record(
        db, AuditAction.SIGNATURE_INSTALLER_DOWNLOADED, user_id=actor.id, entity_type="employee",
        entity_id=employee.id, description=f"Downloaded the Outlook signature installer for {employee.full_name}",
    )
    db.commit()
    return FileResponse(
        installer.INSTALLER_FILE,
        media_type="application/vnd.microsoft.portable-executable",
        filename=installer.installer_filename(employee.id),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/signatures/me/installer")
def my_installer(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _installer_response(db, employee_service.get_employee_for_user(db, user), user)


@router.get("/signatures/{employee_id}/installer")
def employee_installer(employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee = employee_service.get_employee(db, employee_id)
    if user.role != UserRole.ADMIN and employee.user_id != user.id:
        raise AppError(403, "FORBIDDEN", "You can only download your own installer.")
    return _installer_response(db, employee, user)


@public_router.get("/installer/signature")
def installer_signature(
    e: int = Query(..., description="Employee id from the installer file name"),
    s: str = Query(..., max_length=64, description="Key signature from the installer file name"),
    db: Session = Depends(get_db),
):
    """Called by the Windows installer. Public, but only with a valid per-employee key."""
    if not installer.verify_key(e, s):
        raise AppError(403, "INVALID_INSTALLER_KEY", "This installer is not valid. Please download it again from Signature Studio.")
    employee = db.get(Employee, e)
    if employee is None or not employee.is_active:
        raise AppError(403, "EMPLOYEE_INACTIVE", "This employee is not active in Signature Studio.")

    result = signature_service.generate_employee_signature(db, employee.id, live_banner=True)
    audit_service.record(
        db, AuditAction.SIGNATURE_INSTALLED, user_id=employee.user_id, entity_type="employee",
        entity_id=employee.id, description=f"Outlook signature installed for {employee.full_name}",
    )
    db.commit()
    return ok({
        "signature_name": installer.SIGNATURE_NAME,
        "employee_name": employee.full_name,
        "company_name": settings_service.get_app_settings(db).company_name,
        "html": result.html,
        "text": html_to_text(result.html),
    })
