from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request, conflict, not_found
from app.core.security import hash_password
from app.database.models import AuditAction, Employee, OutlookAddinStatus, User, UserRole
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services import audit_service

_PROFILE_FIELDS = [
    "employee_code", "first_name", "last_name", "display_name", "designation", "department",
    "company", "email", "phone", "mobile", "website", "profile_photo_url", "linkedin_url",
    "twitter_url", "instagram_url", "other_social_url", "is_active",
]


def list_employees(
    db: Session,
    *,
    q: str | None = None,
    department: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[Employee], int]:
    stmt = select(Employee)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Employee.first_name.ilike(like),
                Employee.last_name.ilike(like),
                Employee.display_name.ilike(like),
                Employee.email.ilike(like),
                Employee.employee_code.ilike(like),
                Employee.designation.ilike(like),
            )
        )
    if department:
        stmt = stmt.where(Employee.department == department)
    if status == "active":
        stmt = stmt.where(Employee.is_active.is_(True))
    elif status == "inactive":
        stmt = stmt.where(Employee.is_active.is_(False))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Employee.first_name, Employee.last_name, Employee.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total


def list_departments(db: Session) -> list[str]:
    rows = db.scalars(
        select(Employee.department).where(Employee.department.is_not(None)).distinct().order_by(Employee.department)
    ).all()
    return [r for r in rows if r]


def get_employee(db: Session, employee_id: int) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise not_found("Employee")
    return employee


def get_employee_for_user(db: Session, user: User) -> Employee:
    employee = db.scalar(select(Employee).where(Employee.user_id == user.id))
    if employee is None:
        raise not_found("Employee profile")
    return employee


def _ensure_unique(db: Session, data: EmployeeCreate | EmployeeUpdate, exclude_id: int | None = None) -> None:
    code_q = select(Employee.id).where(Employee.employee_code == data.employee_code)
    email_q = select(Employee.id).where(Employee.email == data.email)
    if exclude_id is not None:
        code_q = code_q.where(Employee.id != exclude_id)
        email_q = email_q.where(Employee.id != exclude_id)
    if db.scalar(code_q) is not None:
        raise conflict("DUPLICATE_EMPLOYEE_CODE", f"Employee ID {data.employee_code} is already in use.")
    if db.scalar(email_q) is not None:
        raise conflict("DUPLICATE_EMAIL", f"An employee with email {data.email} already exists.")


def _sync_login(db: Session, employee: Employee, password: str | None) -> None:
    """Keep the linked login account in step with the employee record."""
    user = employee.user
    if user is None and password:
        if db.scalar(select(User.id).where(User.email == employee.email)) is not None:
            raise conflict("DUPLICATE_EMAIL", "A login account already uses this email address.")
        user = User(email=employee.email, password_hash=hash_password(password), role=UserRole.EMPLOYEE)
        db.add(user)
        db.flush()
        employee.user_id = user.id
        employee.user = user
    elif user is not None:
        if user.email != employee.email:
            clash = db.scalar(select(User.id).where(User.email == employee.email, User.id != user.id))
            if clash is not None:
                raise conflict("DUPLICATE_EMAIL", "A login account already uses this email address.")
            user.email = employee.email
        if password:
            user.password_hash = hash_password(password)
        if user.role == UserRole.EMPLOYEE:
            user.is_active = employee.is_active


def create_employee(db: Session, data: EmployeeCreate, actor: User) -> Employee:
    _ensure_unique(db, data)
    employee = Employee(**data.model_dump(include=set(_PROFILE_FIELDS)))
    db.add(employee)
    db.flush()
    _sync_login(db, employee, data.password)
    audit_service.record(
        db, AuditAction.EMPLOYEE_CREATED, user_id=actor.id, entity_type="employee",
        entity_id=employee.id, description=f"Created employee {employee.full_name} ({employee.employee_code})",
    )
    db.commit()
    db.refresh(employee)
    return employee


_NEXUS_MANAGED_MSG = "This employee is managed in nexusAuth. Make this change in nexusAuth; it syncs here automatically."


def _keep_nexus_fields(employee: Employee, data: EmployeeUpdate) -> EmployeeUpdate:
    """For a nexusAuth-linked employee, nexusAuth's values win for every synced field."""
    if not employee.managed_by_nexus:
        return data
    from app.services.nexus_sync import NEXUS_PHOTO_PREFIX, SYNCED_FIELDS

    editable = type(data).model_fields
    kept = {name: getattr(employee, name) for name in SYNCED_FIELDS if name in editable}
    if (employee.profile_photo_url or "").startswith(NEXUS_PHOTO_PREFIX):
        kept["profile_photo_url"] = employee.profile_photo_url  # the photo comes from nexusAuth
    return data.model_copy(update=kept)


def update_employee(db: Session, employee_id: int, data: EmployeeUpdate, actor: User) -> Employee:
    employee = get_employee(db, employee_id)
    data = _keep_nexus_fields(employee, data)
    _ensure_unique(db, data, exclude_id=employee.id)
    if employee.user_id == actor.id and not data.is_active:
        raise bad_request("CANNOT_DEACTIVATE_SELF", "You cannot deactivate your own account.")
    was_active = employee.is_active
    for name, value in data.model_dump(include=set(_PROFILE_FIELDS)).items():
        setattr(employee, name, value)
    _sync_login(db, employee, data.password)
    audit_service.record(
        db, AuditAction.EMPLOYEE_UPDATED, user_id=actor.id, entity_type="employee",
        entity_id=employee.id, description=f"Updated employee {employee.full_name}",
    )
    if was_active != employee.is_active:
        _record_status(db, employee, actor)
    db.commit()
    db.refresh(employee)
    return employee


def _record_status(db: Session, employee: Employee, actor: User) -> None:
    action = AuditAction.EMPLOYEE_ACTIVATED if employee.is_active else AuditAction.EMPLOYEE_DEACTIVATED
    verb = "Activated" if employee.is_active else "Deactivated"
    audit_service.record(
        db, action, user_id=actor.id, entity_type="employee", entity_id=employee.id,
        description=f"{verb} employee {employee.full_name}",
    )


def set_status(db: Session, employee_id: int, is_active: bool, actor: User) -> Employee:
    employee = get_employee(db, employee_id)
    if employee.managed_by_nexus and employee.is_active != is_active:
        raise conflict("MANAGED_BY_NEXUSAUTH", _NEXUS_MANAGED_MSG)
    if employee.user_id == actor.id and not is_active:
        raise bad_request("CANNOT_DEACTIVATE_SELF", "You cannot deactivate your own account.")
    if employee.is_active != is_active:
        employee.is_active = is_active
        if employee.user is not None and employee.user.role == UserRole.EMPLOYEE:
            employee.user.is_active = is_active
        _record_status(db, employee, actor)
        db.commit()
        db.refresh(employee)
    return employee


def delete_employee(db: Session, employee_id: int, actor: User) -> None:
    employee = get_employee(db, employee_id)
    if employee.managed_by_nexus:
        raise conflict("MANAGED_BY_NEXUSAUTH", _NEXUS_MANAGED_MSG)
    if employee.user_id == actor.id:
        raise AppError(400, "CANNOT_DELETE_SELF", "You cannot delete your own account.")
    user = employee.user
    name, code = employee.full_name, employee.employee_code
    db.execute(delete(OutlookAddinStatus).where(OutlookAddinStatus.employee_id == employee.id))
    db.delete(employee)
    if user is not None and user.role == UserRole.EMPLOYEE:
        db.delete(user)
    audit_service.record(
        db, AuditAction.EMPLOYEE_DELETED, user_id=actor.id, entity_type="employee",
        entity_id=employee_id, description=f"Deleted employee {name} ({code})",
    )
    db.commit()
