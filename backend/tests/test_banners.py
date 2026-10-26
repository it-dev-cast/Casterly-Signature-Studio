from datetime import datetime, timedelta, timezone

from tests.conftest import banner_payload, create_banner, current_banner, publish


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_create_banner_is_draft(client, admin_headers):
    b = create_banner(client, admin_headers, "Company Anniversary", title="Celebrating 10 Years")
    assert b["status"] == "DRAFT" and b["effective_status"] == "DRAFT"
    assert b["image_public_url"] == "https://sig.test/uploads/banners/company-anniversary.png"
    assert "<img" in b["html"] and "Celebrating 10 Years" in b["html"]
    assert b["created_by_email"] == "admin@test.com"


def test_invalid_banner_rejected(client, admin_headers):
    """TEST 9"""
    invalid = [
        {"name": ""},
        {"title": "   "},
        {"image_url": ""},
        {"image_url": "not a url"},
        {"image_url": "C:\\images\\banner.png"},
        {"image_url": "/uploads/../../etc/passwd"},
        {"target_url": "ftp://example.com"},
        {"target_url": "javascript:alert(1)"},
        {"start_date": "not-a-date"},
    ]
    for override in invalid:
        r = client.post("/api/banners", json=banner_payload(**override), headers=admin_headers)
        assert r.status_code == 422, override
        assert r.json()["success"] is False
    assert client.get("/api/banners", headers=admin_headers).json()["data"] == []


def test_end_date_before_start_date_rejected(client, admin_headers):
    """TEST 10"""
    start = datetime(2026, 12, 31, tzinfo=timezone.utc)
    r = client.post(
        "/api/banners",
        json=banner_payload(start_date=_iso(start), end_date=_iso(start - timedelta(days=1))),
        headers=admin_headers,
    )
    assert r.status_code == 422
    assert "End date must be after the start date" in r.json()["error"]["message"]


def test_dates_are_normalised_to_utc(client, admin_headers):
    b = create_banner(client, admin_headers, start_date="2027-01-01T09:00:00+05:30")
    assert b["start_date"].startswith("2027-01-01T03:30:00")


def test_only_one_banner_published(client, admin_headers):
    a = create_banner(client, admin_headers, "A")
    b = create_banner(client, admin_headers, "B")
    publish(client, admin_headers, a["id"])
    publish(client, admin_headers, b["id"])
    statuses = {x["name"]: x["status"] for x in client.get("/api/banners", headers=admin_headers).json()["data"]}
    assert statuses == {"A": "DRAFT", "B": "PUBLISHED"}


def test_publish_already_published_conflict(client, admin_headers):
    a = create_banner(client, admin_headers)
    publish(client, admin_headers, a["id"])
    r = publish(client, admin_headers, a["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "ALREADY_PUBLISHED"


def test_publish_expired_banner_rejected(client, admin_headers):
    past_end = datetime.now(timezone.utc) - timedelta(days=1)
    a = create_banner(client, admin_headers, end_date=_iso(past_end))
    r = publish(client, admin_headers, a["id"])
    assert r.status_code == 400 and r.json()["error"]["code"] == "BANNER_EXPIRED"
    assert current_banner(client, admin_headers) is None


def test_scheduled_banner_is_not_current_until_start(client, admin_headers):
    future = datetime.now(timezone.utc) + timedelta(days=3)
    a = create_banner(client, admin_headers, start_date=_iso(future))
    r = publish(client, admin_headers, a["id"])
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "PUBLISHED"
    assert r.json()["data"]["effective_status"] == "SCHEDULED"
    assert current_banner(client, admin_headers) is None


def test_unpublish_only_published(client, admin_headers):
    a = create_banner(client, admin_headers)
    r = client.post(f"/api/banners/{a['id']}/unpublish", headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "NOT_PUBLISHED"


def test_archive_published_removes_from_current(client, admin_headers):
    a = create_banner(client, admin_headers)
    publish(client, admin_headers, a["id"])
    r = client.post(f"/api/banners/{a['id']}/archive", headers=admin_headers)
    assert r.status_code == 200 and r.json()["data"]["status"] == "ARCHIVED"
    assert current_banner(client, admin_headers) is None


def test_archived_banner_cannot_be_published_or_edited(client, admin_headers):
    a = create_banner(client, admin_headers)
    client.post(f"/api/banners/{a['id']}/archive", headers=admin_headers)
    assert publish(client, admin_headers, a["id"]).json()["error"]["code"] == "BANNER_ARCHIVED"
    r = client.put(f"/api/banners/{a['id']}", json=banner_payload("Edited"), headers=admin_headers)
    assert r.status_code == 409
    r = client.post(f"/api/banners/{a['id']}/archive", headers=admin_headers)
    assert r.json()["error"]["code"] == "ALREADY_ARCHIVED"


def test_edit_published_banner_updates_signatures_live(client, admin_headers, template, john):
    a = create_banner(client, admin_headers)
    publish(client, admin_headers, a["id"])
    r = client.put(f"/api/banners/{a['id']}", json=banner_payload("A", image_url="https://cdn.example.com/new.png"),
                   headers=admin_headers)
    assert r.status_code == 200 and r.json()["data"]["status"] == "PUBLISHED"
    html = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]["html"]
    assert "https://cdn.example.com/new.png" in html


def test_delete_rules(client, admin_headers):
    a = create_banner(client, admin_headers)
    publish(client, admin_headers, a["id"])
    r = client.delete(f"/api/banners/{a['id']}", headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "BANNER_PUBLISHED"
    client.post(f"/api/banners/{a['id']}/unpublish", headers=admin_headers)
    assert client.delete(f"/api/banners/{a['id']}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/banners/{a['id']}", headers=admin_headers).status_code == 404


def test_status_filter(client, admin_headers):
    a = create_banner(client, admin_headers, "A")
    create_banner(client, admin_headers, "B")
    publish(client, admin_headers, a["id"])
    names = lambda s: [x["name"] for x in client.get(f"/api/banners?status={s}", headers=admin_headers).json()["data"]]
    assert names("PUBLISHED") == ["A"]
    assert names("DRAFT") == ["B"]
    assert names("ARCHIVED") == []


def test_preview_unsaved_banner_uses_shared_renderer(client, admin_headers):
    from app.renderers.banner import render_banner_html
    from app.renderers.context import BannerView

    payload = banner_payload("Preview Me")
    r = client.post("/api/banners/preview", json=payload, headers=admin_headers)
    assert r.status_code == 200
    expected = render_banner_html(BannerView(
        title=payload["title"],
        image_src="https://sig.test" + payload["image_url"],
        target_url=payload["target_url"],
    ))
    assert r.json()["data"]["html"] == expected


def test_current_banner_none_when_nothing_published(client, admin_headers):
    create_banner(client, admin_headers)
    assert current_banner(client, admin_headers) is None
