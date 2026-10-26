"""nexusAuth -> Signature Studio employee sync, against a fake nexusAuth API."""
import json

import httpx
import pytest
from sqlalchemy import select

from app.database.models import AuditLog, Employee, User
from app.services import nexus_sync
from app.services.nexus_sync import NexusAuthClient, map_employee, sync_employees
from tests.conftest import EMPLOYEE_PASSWORD, login, make_employee


def nexus_employee(nexus_id, email, **overrides):
    data = {
        "id": nexus_id, "company_id": 1, "first_name": "Ravi", "last_name": "Kiran", "full_name": "Ravi Kiran",
        "email": email, "employee_code": f"CN{nexus_id:04d}", "designation": "Engineer", "job_role": "Technician",
        "phone_number": "+91 98450 12345", "linkedin_url": "https://linkedin.com/in/ravi", "department": "IT",
        "status": "active", "pan_number": "ABCDE1234F", "aadhaar_number": "123412341234",
        "bank_account_number": "0001112223",
    }
    data.update(overrides)
    return data


class FakeNexus:
    """Just enough of nexusAuth's API: login, refresh, paged employees and companies."""

    def __init__(self, employees, password="nexus-pass", files=None):
        self.employees = employees
        self.password = password
        self.files = files or {}  # path -> bytes nexusAuth serves publicly (uploaded photos)
        self.logins = 0
        self.expired = False
        self.requests = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path, dict(request.url.params)))
        path = request.url.path
        if path.startswith("/uploads/"):  # public, no token needed (like nexusAuth's StaticFiles mount)
            return httpx.Response(200, content=self.files[path]) if path in self.files else httpx.Response(404)
        if path == "/api/v1/auth/login":
            body = json.loads(request.content)
            if body["password"] != self.password:
                return httpx.Response(401, json={"error_code": "AUTH_INVALID_CREDENTIALS"})
            self.logins += 1
            self.expired = False
            return httpx.Response(200, json={"data": {"access_token": f"tok{self.logins}", "refresh_token": "r",
                                                      "expires_in": 900}})
        if path == "/api/v1/auth/refresh":
            return httpx.Response(401, json={})
        if request.headers.get("authorization") != f"Bearer tok{self.logins}" or self.expired:
            return httpx.Response(401, json={"error_code": "AUTH_TOKEN_EXPIRED"})
        limit, offset = int(request.url.params["limit"]), int(request.url.params["offset"])
        if path == "/api/v1/employees":
            assert request.url.params["include_exited"] == "true"
            rows = self.employees
        elif path == "/api/v1/companies":
            rows = [{"id": 1, "name": "Casterly Private Limited"}]
        else:
            return httpx.Response(404, json={})
        page = rows[offset:offset + limit]
        return httpx.Response(200, json={"data": {"items": page, "total": len(rows), "limit": limit,
                                                  "offset": offset, "has_more": offset + limit < len(rows)}})

    def client(self, password="nexus-pass"):
        return NexusAuthClient("http://nexus.test", "sync@casterly.com", password,
                               transport=httpx.MockTransport(self.handler))


def employee_by_email(db, email):
    db.expire_all()
    return db.scalar(select(Employee).where(Employee.email == email))


def test_new_nexus_employees_are_created_with_their_details(db):
    fake = FakeNexus([nexus_employee(1, "Ravi.Kiran@casterly.com"), nexus_employee(2, "asha@casterly.com",
                                                                                   first_name="Asha", last_name="Rao")])
    report = sync_employees(db, fake.client())
    assert report.ok and report.created == 2
    ravi = employee_by_email(db, "ravi.kiran@casterly.com")
    assert (ravi.employee_code, ravi.first_name, ravi.last_name, ravi.designation) == ("CN0001", "Ravi", "Kiran", "Engineer")
    assert (ravi.department, ravi.company, ravi.phone) == ("IT", "Casterly Private Limited", "+91 98450 12345")
    assert ravi.linkedin_url == "https://linkedin.com/in/ravi" and ravi.is_active and ravi.nexus_employee_id == 1


def test_sensitive_nexus_data_is_never_copied():
    values = map_employee(nexus_employee(1, "a@b.com"), {})
    assert not {"pan_number", "aadhaar_number", "bank_account_number"} & set(values)
    assert "ABCDE1234F" not in json.dumps(values)


def test_an_edit_in_nexus_updates_the_next_sync(db):
    fake = FakeNexus([nexus_employee(1, "ravi@casterly.com")])
    client = fake.client()
    sync_employees(db, client)
    fake.employees = [nexus_employee(1, "ravi.k@casterly.com", designation="Lead Engineer", department="R&D")]
    report = sync_employees(db, client)
    assert report.updated == 1
    ravi = employee_by_email(db, "ravi.k@casterly.com")
    assert ravi.designation == "Lead Engineer" and ravi.department == "R&D"
    assert db.scalar(select(Employee).where(Employee.email == "ravi@casterly.com")) is None  # same record, renamed
    assert sync_employees(db, client).unchanged == 1  # nothing changed -> nothing written


def test_existing_employee_is_linked_by_email_not_duplicated(db):
    existing = make_employee(db, code="EMP-7", first="Rajatha", last="P", designation="Developer",
                             email="rajatha18@outlook.com", with_login=False, mobile="+91 90000 00000")
    fake = FakeNexus([nexus_employee(9, "RAJATHA18@outlook.com", first_name="Rajatha", last_name="Prakash",
                                     employee_code="CN0009")])
    report = sync_employees(db, fake.client())
    assert report.updated == 1 and report.created == 0
    db.expire_all()
    linked = db.get(Employee, existing.id)
    assert linked.nexus_employee_id == 9 and linked.last_name == "Prakash" and linked.employee_code == "CN0009"
    assert linked.mobile == "+91 90000 00000"  # Signature Studio-only fields are kept
    assert db.scalar(select(Employee).where(Employee.email == "rajatha18@outlook.com")).id == existing.id


def test_exited_in_nexus_deactivates_here_and_blocks_login(client, db):
    emp = make_employee(db, code="EMP-X", first="John", last="Smith", designation="Dev", email="john@casterly.com")
    fake = FakeNexus([nexus_employee(3, "john@casterly.com", first_name="John", last_name="Smith")])
    sync_employees(db, fake.client())
    login(client, "john@casterly.com", EMPLOYEE_PASSWORD)  # still active
    fake.employees = [nexus_employee(3, "john@casterly.com", first_name="John", last_name="Smith", status="exited")]
    report = sync_employees(db, fake.client())
    assert report.deactivated == 1
    db.expire_all()
    assert db.get(Employee, emp.id).is_active is False
    assert db.get(User, emp.user_id).is_active is False
    r = client.post("/api/auth/login", json={"email": "john@casterly.com", "password": EMPLOYEE_PASSWORD})
    assert r.status_code in (401, 403)


def test_employee_removed_from_nexus_is_deactivated_not_deleted(db):
    fake = FakeNexus([nexus_employee(1, "a@casterly.com"), nexus_employee(2, "b@casterly.com")])
    sync_employees(db, fake.client())
    fake.employees = [nexus_employee(1, "a@casterly.com")]
    assert sync_employees(db, fake.client()).deactivated == 1
    assert employee_by_email(db, "b@casterly.com").is_active is False


def test_paging_and_token_renewal(db):
    fake = FakeNexus([nexus_employee(i, f"e{i}@casterly.com", employee_code=f"CN{i:04d}") for i in range(1, 251)])
    client = fake.client()
    assert sync_employees(db, client).created == 250
    offsets = [p["offset"] for m, path, p in fake.requests if path == "/api/v1/employees"]
    assert offsets == ["0", "100", "200"]
    fake.expired = True  # token revoked in nexusAuth: the client signs in again once
    assert sync_employees(db, client).ok and fake.logins == 2


def test_wrong_password_reports_clearly_and_changes_nothing(db):
    fake = FakeNexus([nexus_employee(1, "a@casterly.com")])
    report = sync_employees(db, fake.client(password="wrong"))
    assert not report.ok and report.login_rejected and "rejected the sign-in" in report.error
    assert db.scalar(select(Employee)) is None


def test_background_sync_stops_retrying_a_refused_password(db, monkeypatch):
    fake = FakeNexus([], password="right")
    monkeypatch.setattr(nexus_sync, "_client_for_settings", lambda: fake.client(password="wrong"))
    monkeypatch.setattr(nexus_sync._state, "client_key", ("u", "e", "p"))
    nexus_sync.run_sync(lambda: db)
    assert nexus_sync._state.rejected_key == ("u", "e", "p") and nexus_sync.status()["paused"]
    nexus_sync._state.rejected_key = None


def test_clashing_employee_id_falls_back_and_is_reported(db):
    make_employee(db, code="CN0001", first="Local", last="Person", designation="Dev", email="local@casterly.com",
                  with_login=False)
    report = sync_employees(db, FakeNexus([nexus_employee(1, "ravi@casterly.com")]).client())
    assert report.created == 1 and "synced as NX-1" in report.problems[0]
    assert employee_by_email(db, "ravi@casterly.com").employee_code == "NX-1"


def test_missing_optional_values_and_old_nexus_versions(db):
    old = {"id": 5, "company_id": 2, "full_name": "Meera Iyer", "email": "meera@casterly.com",
           "job_role": "Manager", "status": "onboarded", "phone_number": "not a phone"}
    sync_employees(db, FakeNexus([old]).client())
    meera = employee_by_email(db, "meera@casterly.com")
    assert (meera.first_name, meera.last_name, meera.designation, meera.employee_code) == ("Meera", "Iyer", "Manager", "NX-5")
    assert meera.phone is None and meera.company is None and meera.is_active


def test_address_syncs_from_nexus_and_older_versions_never_wipe_it(db):
    fake = FakeNexus([nexus_employee(1, "ravi@casterly.com", address="  No. 12, MG Road \n\n Bengaluru ")])
    sync_employees(db, fake.client())
    assert employee_by_email(db, "ravi@casterly.com").address == "No. 12, MG Road\nBengaluru"
    fake.employees = [nexus_employee(1, "ravi@casterly.com")]  # a nexusAuth without the address field
    sync_employees(db, fake.client())
    assert employee_by_email(db, "ravi@casterly.com").address == "No. 12, MG Road\nBengaluru"
    fake.employees = [nexus_employee(1, "ravi@casterly.com", address=None)]  # cleared in nexusAuth
    sync_employees(db, fake.client())
    assert employee_by_email(db, "ravi@casterly.com").address is None


def test_synced_fields_are_locked_in_signature_studio(client, db, admin_headers):
    sync_employees(db, FakeNexus([nexus_employee(1, "ravi@casterly.com")]).client())
    ravi = employee_by_email(db, "ravi@casterly.com")
    payload = {"employee_code": "HACK", "first_name": "X", "last_name": "Y", "designation": "CEO",
               "email": "other@casterly.com", "mobile": "+91 91111 22222", "is_active": True}
    r = client.put(f"/api/employees/{ravi.id}", json=payload, headers=admin_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert (data["employee_code"], data["first_name"], data["email"]) == ("CN0001", "Ravi", "ravi@casterly.com")
    assert data["mobile"] == "+91 91111 22222" and data["managed_by_nexus"] is True
    assert client.delete(f"/api/employees/{ravi.id}", headers=admin_headers).json()["error"]["code"] == "MANAGED_BY_NEXUSAUTH"
    r = client.patch(f"/api/employees/{ravi.id}/status", json={"is_active": False}, headers=admin_headers)
    assert r.status_code == 409


def test_sync_is_audited(db):
    sync_employees(db, FakeNexus([nexus_employee(1, "ravi@casterly.com")]).client())
    log = db.scalar(select(AuditLog).where(AuditLog.entity_type == "employee"))
    assert "from nexusAuth" in log.description and log.user_id is None


def test_integration_endpoints(client, admin_headers, john_headers):
    status = client.get("/api/integrations/nexusauth", headers=admin_headers).json()["data"]
    assert status["enabled"] is False and "email" in status["synced_fields"]
    r = client.post("/api/integrations/nexusauth/sync", headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "NEXUSAUTH_NOT_CONFIGURED"
    assert client.get("/api/integrations/nexusauth", headers=john_headers).status_code == 403


@pytest.fixture(autouse=True)
def _reset_state():
    yield
    nexus_sync._state.last = None
    nexus_sync._state.rejected_key = None


# ------------------------------------------------------------------ photos --
def _png(color=(200, 30, 30)) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    return tmp_path


def test_photo_uploaded_in_nexus_is_copied_here(db, uploads):
    ref = "/uploads/employee_photos/abc123.png"
    fake = FakeNexus([nexus_employee(1, "ravi@casterly.com", photo_reference=ref)], files={ref: _png()})
    report = sync_employees(db, fake.client())
    photo = employee_by_email(db, "ravi@casterly.com").profile_photo_url
    assert report.ok and photo.startswith("/uploads/photos/nexus-") and photo.endswith(".png")
    assert (uploads / photo.removeprefix("/uploads/")).read_bytes() == fake.files[ref]
    downloads = sum(1 for _, path, _ in fake.requests if path == ref)
    assert sync_employees(db, fake.client()).unchanged == 1  # unchanged photo: not downloaded again
    assert sum(1 for _, path, _ in fake.requests if path == ref) == downloads


def test_changed_and_removed_nexus_photos_follow(db, uploads):
    old, new = "/uploads/employee_photos/old.png", "/uploads/employee_photos/new.png"
    fake = FakeNexus([nexus_employee(1, "ravi@casterly.com", photo_reference=old)],
                     files={old: _png(), new: _png((0, 0, 255))})
    sync_employees(db, fake.client())
    first = employee_by_email(db, "ravi@casterly.com").profile_photo_url
    fake.employees = [nexus_employee(1, "ravi@casterly.com", photo_reference=new)]
    assert sync_employees(db, fake.client()).updated == 1
    second = employee_by_email(db, "ravi@casterly.com").profile_photo_url
    assert second != first and (uploads / second.removeprefix("/uploads/")).read_bytes() == fake.files[new]
    fake.employees = [nexus_employee(1, "ravi@casterly.com", photo_reference=None)]
    sync_employees(db, fake.client())
    assert employee_by_email(db, "ravi@casterly.com").profile_photo_url is None


def test_photo_added_here_is_kept_while_nexus_has_none(db, uploads):
    fake = FakeNexus([nexus_employee(1, "ravi@casterly.com")])
    sync_employees(db, fake.client())
    ravi = employee_by_email(db, "ravi@casterly.com")
    ravi.profile_photo_url = "/uploads/photos/own.png"
    db.commit()
    sync_employees(db, fake.client())
    assert employee_by_email(db, "ravi@casterly.com").profile_photo_url == "/uploads/photos/own.png"


def test_bad_or_missing_nexus_photos_never_break_the_sync(db, uploads):
    fake = FakeNexus([
        nexus_employee(1, "a@casterly.com", photo_reference="/uploads/employee_photos/missing.png"),
        nexus_employee(2, "b@casterly.com", photo_reference="/uploads/employee_photos/fake.png"),
        nexus_employee(3, "c@casterly.com", photo_reference="/api/v1/../secrets"),
        nexus_employee(4, "d@casterly.com", photo_reference="https://cdn.example.com/d.jpg"),
    ], files={"/uploads/employee_photos/fake.png": b"<script>not an image</script>"})
    report = sync_employees(db, fake.client())
    assert report.ok and report.created == 4
    assert all(employee_by_email(db, f"{x}@casterly.com").profile_photo_url is None for x in "abc")
    assert employee_by_email(db, "d@casterly.com").profile_photo_url == "https://cdn.example.com/d.jpg"
    text = " ".join(report.problems)
    assert "a@casterly.com could not be copied" in text and "HTTP 404" in text
    assert "b@casterly.com in nexusAuth was not used" in text
    assert "c@casterly.com in nexusAuth was not used: unexpected location" in text
    assert not any(path.startswith("/api/v1/..") for _, path, _ in fake.requests)


def test_nexus_photo_cannot_be_replaced_in_signature_studio(client, db, admin_headers, uploads):
    ref = "/uploads/employee_photos/abc.png"
    sync_employees(db, FakeNexus([nexus_employee(1, "ravi@casterly.com", photo_reference=ref)],
                                 files={ref: _png()}).client())
    ravi = employee_by_email(db, "ravi@casterly.com")
    photo = ravi.profile_photo_url
    payload = {"employee_code": ravi.employee_code, "first_name": "Ravi", "designation": "Engineer",
               "email": "ravi@casterly.com", "profile_photo_url": "/uploads/photos/other.png", "is_active": True}
    r = client.put(f"/api/employees/{ravi.id}", json=payload, headers=admin_headers)
    assert r.status_code == 200 and r.json()["data"]["profile_photo_url"] == photo
