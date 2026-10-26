import os
import re
import tempfile
from pathlib import Path


def _test_database_url() -> str:
    """The PostgreSQL database the suite runs against: TEST_DATABASE_URL (environment, or backend/.env).

    Every test drops and recreates all tables there, so it must be a separate database whose name
    ends in "_test" - never the real one.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        env_file = Path(__file__).resolve().parents[1] / ".env"
        if env_file.is_file():
            m = re.search(r"(?m)^TEST_DATABASE_URL=(.+?)\s*$", env_file.read_text(encoding="utf-8"))
            url = m.group(1) if m else None
    if not url:
        raise RuntimeError(
            "Set TEST_DATABASE_URL (environment or backend/.env) to a PostgreSQL test database, e.g. "
            "postgresql+psycopg://user:pass@localhost:5432/signature_studio_test"
        )
    if not url.rstrip("/").rsplit("/", 1)[-1].split("?")[0].endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL must point at a database whose name ends in '_test'; "
                           "the tests wipe it on every run.")
    return url


# Configure the app for tests BEFORE anything from `app` is imported.
TEST_DATABASE_URL = _test_database_url()
_UPLOADS = tempfile.mkdtemp(prefix="sigstudio-uploads-")
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-0123456789abcdef"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL  # the app's own engine must never reach the real database
os.environ["PUBLIC_BASE_URL"] = "https://sig.test"
os.environ["UPLOAD_DIR"] = _UPLOADS
os.environ["NEXUSAUTH_URL"] = ""  # no background sync in tests

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import models  # noqa: E402,F401
from app.database.database import Base, get_db  # noqa: E402
from app.database.models import Employee, SignatureTemplate, User, UserRole  # noqa: E402
from app.main import app  # noqa: E402

ADMIN_PASSWORD = "AdminPass#1"
EMPLOYEE_PASSWORD = "EmployeePass#1"


def reset_database(eng) -> None:
    """Empty the test database: all tables, plus alembic_version left by test_migrations."""
    Base.metadata.drop_all(eng)
    with eng.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))


@pytest.fixture
def engine():
    eng = create_engine(TEST_DATABASE_URL)
    reset_database(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()  # release pooled connections so the next reset isn't blocked
    reset_database(eng)
    eng.dispose()


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ----------------------------------------------------------------- helpers --
def login(client, email: str, password: str) -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


@pytest.fixture
def admin(db) -> User:
    user = User(email="admin@test.com", password_hash=hash_password(ADMIN_PASSWORD), role=UserRole.ADMIN)
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def admin_headers(client, admin) -> dict:
    return login(client, admin.email, ADMIN_PASSWORD)


@pytest.fixture
def template(db) -> SignatureTemplate:
    t = SignatureTemplate(name="Default", layout="classic", is_active=True)
    db.add(t)
    db.commit()
    return t


def make_employee(db, *, code: str, first: str, last: str, designation: str, email: str,
                  department: str | None = None, with_login: bool = True, **extra) -> Employee:
    user_id = None
    if with_login:
        user = User(email=email, password_hash=hash_password(EMPLOYEE_PASSWORD), role=UserRole.EMPLOYEE)
        db.add(user)
        db.flush()
        user_id = user.id
    emp = Employee(employee_code=code, first_name=first, last_name=last, designation=designation,
                   department=department, email=email, user_id=user_id, **extra)
    db.add(emp)
    db.commit()
    return emp


@pytest.fixture
def john(db) -> Employee:
    return make_employee(db, code="EMP-A", first="John", last="Smith", designation="Developer",
                         department="Engineering", email="john@company.com", phone="+1 555 0100")


@pytest.fixture
def priya(db) -> Employee:
    return make_employee(db, code="EMP-B", first="Priya", last="Patel", designation="HR Manager",
                         department="Human Resources", email="priya@company.com", mobile="+44 20 7946 0000")


@pytest.fixture
def john_headers(client, john) -> dict:
    return login(client, john.email, EMPLOYEE_PASSWORD)


def banner_payload(name: str = "Banner A", **overrides) -> dict:
    data = {
        "name": name,
        "title": f"{name} title",
        "description": "Test banner",
        "image_url": f"/uploads/banners/{name.lower().replace(' ', '-')}.png",
        "target_url": "https://example.com/campaign",
    }
    data.update(overrides)
    return data


def create_banner(client, headers, name: str = "Banner A", **overrides) -> dict:
    r = client.post("/api/banners", json=banner_payload(name, **overrides), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["data"]


def publish(client, headers, banner_id: int):
    return client.post(f"/api/banners/{banner_id}/publish", headers=headers)


def current_banner(client, headers) -> dict | None:
    r = client.get("/api/banners/current", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]["banner"]
