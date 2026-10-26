"""Role enforcement happens on the backend, not just by hiding buttons."""
import pytest

from tests.conftest import banner_payload, create_banner


def test_employee_cannot_publish_banner(client, admin_headers, john_headers):
    """TEST 7"""
    banner = create_banner(client, admin_headers, "Banner A")
    r = client.post(f"/api/banners/{banner['id']}/publish", headers=john_headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"
    detail = client.get(f"/api/banners/{banner['id']}", headers=admin_headers).json()["data"]
    assert detail["status"] == "DRAFT"


def test_employee_cannot_edit_another_employee(client, john_headers, priya):
    """TEST 8"""
    payload = {
        "employee_code": priya.employee_code, "first_name": "Hacked", "last_name": "Name",
        "designation": "CEO", "email": priya.email,
    }
    r = client.put(f"/api/employees/{priya.id}", json=payload, headers=john_headers)
    assert r.status_code == 403
    r = client.patch(f"/api/employees/{priya.id}/status", json={"is_active": False}, headers=john_headers)
    assert r.status_code == 403
    assert client.delete(f"/api/employees/{priya.id}", headers=john_headers).status_code == 403


def test_employee_cannot_edit_self_via_admin_api(client, john_headers, john):
    payload = {"employee_code": john.employee_code, "first_name": "J", "last_name": "S",
               "designation": "CTO", "email": john.email}
    assert client.put(f"/api/employees/{john.id}", json=payload, headers=john_headers).status_code == 403


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/employees"),
        ("post", "/api/employees"),
        ("get", "/api/banners"),
        ("post", "/api/banners"),
        ("post", "/api/banners/preview"),
        ("get", "/api/templates"),
        ("post", "/api/templates"),
        ("get", "/api/overview"),
        ("get", "/api/audit-logs"),
        ("get", "/api/settings"),
        ("put", "/api/settings"),
    ],
)
def test_employee_blocked_from_admin_endpoints(client, john_headers, method, path):
    kwargs = {"json": banner_payload()} if method in ("post", "put") else {}
    r = getattr(client, method)(path, headers=john_headers, **kwargs)
    assert r.status_code == 403, (path, r.text)


def test_employee_cannot_view_other_signature_or_profile(client, john_headers, priya):
    assert client.get(f"/api/signatures/{priya.id}", headers=john_headers).status_code == 403
    assert client.get(f"/api/signatures/{priya.id}/html", headers=john_headers).status_code == 403
    assert client.get(f"/api/employees/{priya.id}", headers=john_headers).status_code == 403


def test_employee_can_view_own_data_and_current_banner(client, john_headers, john, template):
    assert client.get(f"/api/employees/{john.id}", headers=john_headers).status_code == 200
    assert client.get("/api/employees/me", headers=john_headers).status_code == 200
    assert client.get(f"/api/signatures/{john.id}", headers=john_headers).status_code == 200
    assert client.get("/api/signatures/me", headers=john_headers).status_code == 200
    assert client.get("/api/banners/current", headers=john_headers).status_code == 200


def test_unauthenticated_requests_rejected(client, john):
    for path in ("/api/employees", "/api/banners/current", f"/api/signatures/{john.id}/html", "/api/overview"):
        assert client.get(path).status_code == 401
