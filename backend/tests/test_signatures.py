from app.database.models import SignatureTemplate
from tests.conftest import create_banner, make_employee, publish


def test_signature_contains_employee_details_and_links(client, admin_headers, template, john):
    data = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]
    html = data["html"]
    assert data["template"]["name"] == "Default"
    assert "John Smith" in html and "Developer" in html and "Engineering" in html
    assert 'href="mailto:john@company.com"' in html
    assert 'href="tel:+15550100"' in html
    assert "<table" in html and 'role="presentation"' in html


def test_signature_is_email_safe(client, admin_headers, template, john):
    html = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]["html"]
    lowered = html.lower()
    for forbidden in ("<script", "javascript:", "<style", "onerror=", "onclick=", "position:", "display:flex", "grid"):
        assert forbidden not in lowered


def test_user_content_is_escaped(client, db, admin_headers, template):
    emp = make_employee(db, code="EMP-X", first="<script>alert(1)</script>", last="O'Neil",
                        designation='Dev" onmouseover="x', email="x@company.com", with_login=False)
    html = client.get(f"/api/signatures/{emp.id}", headers=admin_headers).json()["data"]["html"]
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert 'Dev" onmouseover' not in html


def test_images_use_absolute_public_urls(client, db, admin_headers, template):
    emp = make_employee(db, code="EMP-P", first="Pia", last="Photo", designation="Designer",
                        email="pia@company.com", profile_photo_url="/uploads/photos/pia.png", with_login=False)
    banner = create_banner(client, admin_headers, "Launch")
    publish(client, admin_headers, banner["id"])
    html = client.get(f"/api/signatures/{emp.id}", headers=admin_headers).json()["data"]["html"]
    assert 'src="https://sig.test/uploads/photos/pia.png"' in html
    assert 'src="https://sig.test/uploads/banners/launch.png"' in html
    assert 'href="https://example.com/campaign"' in html
    assert 'src="/uploads' not in html


def test_html_endpoint_returns_raw_fragment_for_integrations(client, admin_headers, template, john):
    r = client.get(f"/api/signatures/{john.id}/html", headers=admin_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.text.startswith("<table")
    assert r.headers["cache-control"] == "no-store"


def test_html_download_and_preview_are_full_documents(client, admin_headers, template, john):
    r = client.get(f"/api/signatures/{john.id}/html?download=true", headers=admin_headers)
    assert "attachment" in r.headers["content-disposition"]
    assert r.text.startswith("<!DOCTYPE html>")
    r = client.get(f"/api/signatures/{john.id}/preview", headers=admin_headers)
    assert r.status_code == 200 and "<html" in r.text and "John Smith" in r.text


def test_signature_with_selected_template(client, db, admin_headers, template, john):
    minimal = SignatureTemplate(name="Minimal", layout="minimal", is_active=False, primary_color="#111111")
    db.add(minimal)
    db.commit()
    data = client.get(f"/api/signatures/{john.id}?template_id={minimal.id}", headers=admin_headers).json()["data"]
    assert data["template"]["name"] == "Minimal"
    assert "#111111" in data["html"]


def test_signature_falls_back_to_default_design_without_template(client, admin_headers, john):
    data = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]
    assert data["template"] is None
    assert "John Smith" in data["html"]


def test_signature_unknown_employee(client, admin_headers):
    r = client.get("/api/signatures/9999", headers=admin_headers)
    assert r.status_code == 404


def test_company_settings_fallbacks(client, admin_headers, template, john):
    client.put("/api/settings", json={"company_name": "Globex", "company_website": "globex.example",
                                      "legal_disclaimer": "Confidential."}, headers=admin_headers)
    html = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]["html"]
    assert "Globex" in html and "https://globex.example" in html and "Confidential." in html
