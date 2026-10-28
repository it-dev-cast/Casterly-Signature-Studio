import io

from PIL import Image

from tests.conftest import create_banner, publish


def _actions(client, headers) -> list[str]:
    return [i["action"] for i in client.get("/api/audit-logs?page_size=200", headers=headers).json()["data"]["items"]]


# ------------------------------------------------------------------- audit --
def test_audit_log_records_key_actions(client, admin_headers, john):
    a = create_banner(client, admin_headers, "A")
    b = create_banner(client, admin_headers, "B")
    publish(client, admin_headers, a["id"])
    publish(client, admin_headers, b["id"])
    client.post(f"/api/banners/{b['id']}/unpublish", headers=admin_headers)
    client.post(f"/api/banners/{a['id']}/archive", headers=admin_headers)
    client.patch(f"/api/employees/{john.id}/status", json={"is_active": False}, headers=admin_headers)

    actions = _actions(client, admin_headers)
    for expected in ("LOGIN", "BANNER_CREATED", "BANNER_PUBLISHED", "BANNER_UNPUBLISHED",
                     "BANNER_ARCHIVED", "EMPLOYEE_DEACTIVATED"):
        assert expected in actions
    # Publishing B implicitly unpublished A -> two unpublish entries in total.
    assert actions.count("BANNER_UNPUBLISHED") == 2
    assert actions.count("BANNER_PUBLISHED") == 2


def test_audit_log_entry_shape_and_filter(client, admin_headers):
    create_banner(client, admin_headers, "Shape")
    data = client.get("/api/audit-logs?action=BANNER_CREATED", headers=admin_headers).json()["data"]
    assert data["total"] == 1
    entry = data["items"][0]
    assert entry["user_email"] == "admin@test.com"
    assert entry["entity_type"] == "banner"
    assert "Shape" in entry["description"]


def test_audit_log_never_contains_passwords(client, admin_headers):
    client.post("/api/employees", json={
        "employee_code": "E1", "first_name": "A", "last_name": "B", "designation": "C",
        "email": "a@b.com", "password": "SuperSecret#99",
    }, headers=admin_headers)
    client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrong-password"})
    r = client.get("/api/audit-logs?page_size=200", headers=admin_headers)
    assert "SuperSecret#99" not in r.text and "wrong-password" not in r.text


def test_logout_is_audited(client, admin_headers):
    client.post("/api/auth/logout", headers=admin_headers)
    from tests.conftest import ADMIN_PASSWORD, login
    headers = login(client, "admin@test.com", ADMIN_PASSWORD)
    assert "LOGOUT" in _actions(client, headers)


# --------------------------------------------------------------- templates --
TEMPLATE = {"name": "Brand Blue", "layout": "classic", "primary_color": "#0f172a", "accent_color": "#0ea5e9"}


def test_first_template_auto_active_and_activation_is_exclusive(client, admin_headers):
    first = client.post("/api/templates", json=TEMPLATE, headers=admin_headers).json()["data"]
    assert first["is_active"] is True and first["primary_color"] == "#0F172A"
    second = client.post("/api/templates", json={**TEMPLATE, "name": "Other", "layout": "minimal"},
                         headers=admin_headers).json()["data"]
    assert second["is_active"] is False
    client.post(f"/api/templates/{second['id']}/activate", headers=admin_headers)
    active = [t["name"] for t in client.get("/api/templates", headers=admin_headers).json()["data"] if t["is_active"]]
    assert active == ["Other"]
    assert "TEMPLATE_ACTIVATED" in _actions(client, admin_headers)


def test_template_validation(client, admin_headers):
    for bad in ({"layout": "nope"}, {"primary_color": "blue"}, {"font_family": "Arial;} body{x"}, {"name": ""}):
        assert client.post("/api/templates", json={**TEMPLATE, **bad}, headers=admin_headers).status_code == 422
    client.post("/api/templates", json=TEMPLATE, headers=admin_headers)
    r = client.post("/api/templates", json=TEMPLATE, headers=admin_headers)
    assert r.status_code == 409


def test_update_template(client, admin_headers):
    t = client.post("/api/templates", json=TEMPLATE, headers=admin_headers).json()["data"]
    r = client.put(f"/api/templates/{t['id']}", json={**TEMPLATE, "show_photo": False}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["data"]["show_photo"] is False
    layouts = client.get("/api/templates/layouts", headers=admin_headers).json()["data"]
    assert {l["key"] for l in layouts} == {"classic", "minimal"}


# ----------------------------------------------------------------- uploads --
def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (60, 20), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_upload_image_and_serve(client, admin_headers):
    r = client.post("/api/uploads", data={"kind": "banner"},
                    files={"file": ("b.png", _png(), "image/png")}, headers=admin_headers)
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["path"].startswith("/uploads/banners/") and data["path"].endswith(".png")
    assert data["url"] == "https://sig.test" + data["path"]
    served = client.get(data["path"])
    assert served.status_code == 200 and served.content == _png()
    # Clients must re-check uploaded images, so a replaced photo or banner shows up quickly.
    assert served.headers["cache-control"] == "no-cache" and served.headers["etag"]
    again = client.get(data["path"], headers={"If-None-Match": served.headers["etag"]})
    assert again.status_code == 304 and again.headers["cache-control"] == "no-cache"


def test_upload_rejects_non_images(client, admin_headers):
    r = client.post("/api/uploads", data={"kind": "banner"},
                    files={"file": ("evil.png", b"<script>alert(1)</script>", "image/png")}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_IMAGE"
    r = client.post("/api/uploads", data={"kind": "other"},
                    files={"file": ("b.png", _png(), "image/png")}, headers=admin_headers)
    assert r.status_code == 422


def test_upload_requires_admin(client, john_headers):
    r = client.post("/api/uploads", data={"kind": "banner"},
                    files={"file": ("b.png", _png(), "image/png")}, headers=john_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------- overview --
def test_overview(client, admin_headers, template, john, priya):
    create_banner(client, admin_headers, "Draft")
    live = create_banner(client, admin_headers, "Live")
    publish(client, admin_headers, live["id"])
    data = client.get("/api/overview", headers=admin_headers).json()["data"]
    assert data["stats"] == {"total_employees": 2, "active_employees": 2, "draft_banners": 1,
                             "signature_templates": 1, "has_published_banner": True}
    assert data["current_banner"]["name"] == "Live" and "<img" in data["current_banner"]["html"]
    assert data["active_template"]["name"] == "Default"


def test_unhandled_errors_do_not_leak(client, admin_headers, monkeypatch):
    from app.services import template_service

    def boom(*_):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(template_service, "list_templates", boom)
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/templates", headers=admin_headers)
    assert r.status_code == 500
    assert "secret internal detail" not in r.text
    assert r.json()["error"]["code"] == "INTERNAL_ERROR"
