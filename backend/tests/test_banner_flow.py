"""The core product guarantee: one published banner flows into EVERY signature automatically."""
from sqlalchemy import select

from app.database.models import Employee
from tests.conftest import create_banner, current_banner, publish


def _signature(client, headers, employee_id: int) -> dict:
    r = client.get(f"/api/signatures/{employee_id}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_global_banner_flow(client, db, admin_headers, template, john, priya):
    employees_before = {
        e.id: (e.updated_at, e.first_name, e.email) for e in db.scalars(select(Employee)).all()
    }

    # TEST 1 - Create Banner A, publish it, current banner = A.
    a = create_banner(client, admin_headers, "Banner A")
    assert a["status"] == "DRAFT"
    assert publish(client, admin_headers, a["id"]).status_code == 200
    assert current_banner(client, admin_headers)["id"] == a["id"]

    # TEST 2 - Create Banner B, publish it, current = B, A is no longer current.
    b = create_banner(client, admin_headers, "Banner B")
    r = publish(client, admin_headers, b["id"])
    assert r.status_code == 200 and r.json()["data"]["status"] == "PUBLISHED"
    assert current_banner(client, admin_headers)["id"] == b["id"]
    a_now = client.get(f"/api/banners/{a['id']}", headers=admin_headers).json()["data"]
    assert a_now["status"] == "DRAFT" and a_now["is_current"] is False
    published = [x for x in client.get("/api/banners", headers=admin_headers).json()["data"] if x["status"] == "PUBLISHED"]
    assert [x["id"] for x in published] == [b["id"]]

    # TEST 3 - Employee A's signature contains Banner B.
    sig_a = _signature(client, admin_headers, john.id)
    assert sig_a["banner"]["id"] == b["id"]
    assert "banner-b.png" in sig_a["html"] and "banner-a.png" not in sig_a["html"]

    # TEST 4 - Employee B's signature contains Banner B.
    sig_b = _signature(client, admin_headers, priya.id)
    assert sig_b["banner"]["id"] == b["id"]
    assert "banner-b.png" in sig_b["html"]

    # TEST 5 - The two signatures keep their own personal information.
    assert "John Smith" in sig_a["html"] and "Developer" in sig_a["html"] and "john@company.com" in sig_a["html"]
    assert "Priya Patel" in sig_b["html"] and "HR Manager" in sig_b["html"] and "priya@company.com" in sig_b["html"]
    assert "Priya" not in sig_a["html"] and "John" not in sig_b["html"]

    # TEST 6 - Unpublish Banner B: signatures no longer contain any banner.
    r = client.post(f"/api/banners/{b['id']}/unpublish", headers=admin_headers)
    assert r.status_code == 200 and r.json()["data"]["status"] == "DRAFT"
    assert current_banner(client, admin_headers) is None
    for emp in (john, priya):
        sig = _signature(client, admin_headers, emp.id)
        assert sig["banner"] is None
        assert "/uploads/banners/" not in sig["html"]

    # No employee record was modified at any point.
    db.expire_all()
    employees_after = {
        e.id: (e.updated_at, e.first_name, e.email) for e in db.scalars(select(Employee)).all()
    }
    assert employees_after == employees_before


def test_employee_sees_new_banner_in_own_signature(client, admin_headers, john_headers, template, john):
    a = create_banner(client, admin_headers, "Company Anniversary")
    publish(client, admin_headers, a["id"])
    mine = client.get("/api/signatures/me", headers=john_headers).json()["data"]
    assert mine["banner"]["name"] == "Company Anniversary"

    b = create_banner(client, admin_headers, "New Year Campaign")
    publish(client, admin_headers, b["id"])
    mine = client.get("/api/signatures/me", headers=john_headers).json()["data"]
    assert mine["banner"]["name"] == "New Year Campaign"
    assert "new-year-campaign.png" in mine["html"]
