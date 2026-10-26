from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings
from tests.conftest import ADMIN_PASSWORD, EMPLOYEE_PASSWORD, login


def test_login_success_returns_token_and_user(client, admin):
    r = client.post("/api/auth/login", json={"email": "ADMIN@test.com", "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["user"]["role"] == "ADMIN"
    assert body["data"]["access_token"]
    assert "password" not in r.text and "password_hash" not in r.text


def test_password_is_hashed(db, admin):
    assert admin.password_hash != ADMIN_PASSWORD
    assert admin.password_hash.startswith("$argon2")


def test_login_wrong_password(client, admin):
    r = client.post("/api/auth/login", json={"email": admin.email, "password": "wrong"})
    assert r.status_code == 401
    assert r.json() == {"success": False, "error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}}


def test_login_unknown_user_same_error(client):
    r = client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "whatever"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_validation_error_envelope(client):
    r = client.post("/api/auth/login", json={"email": "not-an-email", "password": ""})
    assert r.status_code == 422
    assert r.json()["success"] is False
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_inactive_employee_cannot_login(client, db, john):
    john.is_active = False
    john.user.is_active = False
    db.commit()
    r = client.post("/api/auth/login", json={"email": john.email, "password": EMPLOYEE_PASSWORD})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ACCOUNT_DISABLED"


def test_me_returns_user_and_employee_profile(client, john):
    headers = login(client, john.email, EMPLOYEE_PASSWORD)
    data = client.get("/api/auth/me", headers=headers).json()["data"]
    assert data["user"]["role"] == "EMPLOYEE"
    assert data["employee"]["employee_code"] == "EMP-A"


def test_missing_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_invalid_token(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_TOKEN"


def test_expired_token(client, admin):
    s = get_settings()
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    token = jwt.encode({"sub": str(admin.id), "role": "ADMIN", "jti": "x", "exp": past}, s.secret_key, algorithm="HS256")
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "TOKEN_EXPIRED"
    assert r.json()["error"]["message"] == "Your session has expired. Please login again."


def test_token_signed_with_other_key_rejected(client, admin):
    token = jwt.encode({"sub": str(admin.id), "jti": "x", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                       "another-secret-key-that-is-long-enough-000000", algorithm="HS256")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logout_revokes_token(client, admin_headers):
    assert client.get("/api/auth/me", headers=admin_headers).status_code == 200
    assert client.post("/api/auth/logout", headers=admin_headers).status_code == 200
    r = client.get("/api/auth/me", headers=admin_headers)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "TOKEN_REVOKED"


def test_remember_me_issues_longer_token(client, admin):
    short = client.post("/api/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}).json()["data"]
    long = client.post(
        "/api/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD, "remember_me": True}
    ).json()["data"]
    assert long["expires_at"] > short["expires_at"]
