from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin
from app.core.errors import AppError
from app.database.database import get_db
from app.database.models import User, UserRole
from app.schemas.common import ApiResponse, Page, ok
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeStatusUpdate, EmployeeUpdate
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=ApiResponse[Page[EmployeeRead]])
def list_employees(
    q: str | None = Query(default=None, max_length=100),
    department: str | None = Query(default=None, max_length=150),
    status: Literal["active", "inactive", "all"] = "all",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    items, total = employee_service.list_employees(
        db, q=q, department=department, status=status, page=page, page_size=page_size
    )
    return ok({"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/departments", response_model=ApiResponse[list[str]])
def departments(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return ok(employee_service.list_departments(db))


@router.get("/me", response_model=ApiResponse[EmployeeRead])
def my_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ok(employee_service.get_employee_for_user(db, user))


@router.post("", response_model=ApiResponse[EmployeeRead], status_code=status.HTTP_201_CREATED)
def create_employee(body: EmployeeCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return ok(employee_service.create_employee(db, body, admin))


@router.get("/{employee_id}", response_model=ApiResponse[EmployeeRead])
def get_employee(employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee = employee_service.get_employee(db, employee_id)
    if user.role != UserRole.ADMIN and employee.user_id != user.id:
        raise AppError(403, "FORBIDDEN", "You can only view your own profile.")
    return ok(employee)


@router.put("/{employee_id}", response_model=ApiResponse[EmployeeRead])
def update_employee(
    employee_id: int, body: EmployeeUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    return ok(employee_service.update_employee(db, employee_id, body, admin))


@router.patch("/{employee_id}/status", response_model=ApiResponse[EmployeeRead])
def set_status(
    employee_id: int, body: EmployeeStatusUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
):
    return ok(employee_service.set_status(db, employee_id, body.is_active, admin))


@router.delete("/{employee_id}", response_model=ApiResponse[dict])
def delete_employee(employee_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    employee_service.delete_employee(db, employee_id, admin)
    return ok({"deleted": True})
