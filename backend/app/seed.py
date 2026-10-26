"""Seed development data.  Run:  python -m app.seed

Idempotent: records that already exist (matched by email / name) are skipped.
The credentials below are for LOCAL DEVELOPMENT ONLY - never use them in production.
"""
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.database import SessionLocal
from app.database.models import (
    AppSettings,
    Banner,
    BannerStatus,
    Employee,
    SignatureTemplate,
    User,
    UserRole,
)
from app.database.types import utcnow
from app.services.storage_service import get_storage
from app.utils.placeholder_images import avatar_png, banner_png

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@12345"
EMPLOYEE_PASSWORD = "Employee@123"

EMPLOYEES = [
    dict(employee_code="EMP-001", first_name="John", last_name="Carter", designation="Software Developer",
         department="Engineering", email="john.carter@example.com", phone="+1 (555) 010-2001",
         linkedin_url="https://www.linkedin.com/in/example-john", color="#2563EB"),
    dict(employee_code="EMP-002", first_name="Priya", last_name="Nair", designation="HR Manager",
         department="Human Resources", email="priya.nair@example.com", phone="+1 (555) 010-2002",
         mobile="+1 (555) 010-3002", linkedin_url="https://www.linkedin.com/in/example-priya", color="#DB2777"),
    dict(employee_code="EMP-003", first_name="Alex", last_name="Morgan", designation="Account Executive",
         department="Sales", email="alex.morgan@example.com", mobile="+1 (555) 010-3003",
         twitter_url="https://x.com/example", color="#059669"),
]


def _save(data: bytes, key: str) -> str:
    return get_storage().save(data, key)


def run() -> None:
    db = SessionLocal()
    try:
        if db.get(AppSettings, 1) is None:
            db.add(AppSettings(
                id=1,
                company_name="Casterly Private Limited",
                show_logo_in_signature=True,
                legal_disclaimer="This email and any attachments are confidential and intended solely for the addressee.",
            ))

        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if admin is None:
            admin = User(email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD), role=UserRole.ADMIN)
            db.add(admin)
            db.flush()

        for spec in EMPLOYEES:
            spec = dict(spec)
            color = spec.pop("color")
            if db.scalar(select(Employee).where(Employee.email == spec["email"])):
                continue
            user = User(email=spec["email"], password_hash=hash_password(EMPLOYEE_PASSWORD), role=UserRole.EMPLOYEE)
            db.add(user)
            db.flush()
            initials = spec["first_name"][0] + spec["last_name"][0]
            photo = _save(avatar_png(initials, color), f"photos/seed-{spec['employee_code'].lower()}.png")
            db.add(Employee(**spec, profile_photo_url=photo, user_id=user.id))

        if db.scalar(select(SignatureTemplate).limit(1)) is None:
            db.add(SignatureTemplate(
                name="Corporate Classic",
                description="Default company signature with photo, contact details and banner.",
                layout="classic", is_active=True,
            ))
            db.add(SignatureTemplate(
                name="Minimal Text",
                description="Compact text-only signature.",
                layout="minimal", is_active=False,
            ))

        if db.scalar(select(Banner).limit(1)) is None:
            launch = _save(banner_png("Product Launch 2026", "Discover what's new at example.com"),
                           "banners/seed-product-launch.png")
            holiday = _save(banner_png("Season's Greetings", "Warm wishes from all of us", "#7F1D1D", "#F59E0B"),
                            "banners/seed-holiday.png")
            db.add(Banner(name="Product Launch 2026", title="Discover our new platform",
                          description="Spring product launch campaign.", image_url=launch,
                          target_url="https://www.example.com/launch", status=BannerStatus.PUBLISHED,
                          published_at=utcnow(), created_by=admin.id))
            db.add(Banner(name="Holiday Greetings", title="Season's Greetings",
                          description="End-of-year holiday banner.", image_url=holiday,
                          target_url="https://www.example.com", status=BannerStatus.DRAFT, created_by=admin.id))

        db.commit()
    finally:
        db.close()

    print("Seed complete.")
    print(f"  Admin:     {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"  Employees: {', '.join(e['email'] for e in EMPLOYEES)} / {EMPLOYEE_PASSWORD}")
    print(f"  Images served from {get_settings().public_base_url}/uploads/")


if __name__ == "__main__":
    run()
