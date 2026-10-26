"""'Send email' setup flow: email to the employee with a personal setup link and page."""
import pytest

from app.api import setup
from app.core.config import get_settings


class FakeSMTP:
    sent: list = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, context=None):
        pass

    def login(self, user, password):
        self.user = user

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.sent = []
    s = get_settings()
    monkeypatch.setattr(s, "smtp_host", "smtp.test")
    monkeypatch.setattr(s, "smtp_username", "signatures@casterly.test")
    monkeypatch.setattr(s, "smtp_password", "x")
    monkeypatch.setattr(s, "smtp_from", "Casterly Signatures <signatures@casterly.test>")
    monkeypatch.setattr("app.services.email_service.smtplib.SMTP", FakeSMTP)
    return FakeSMTP


def test_send_email_delivers_signature_and_personal_link(client, admin_headers, template, john, smtp):
    r = client.post(f"/api/signatures/{john.id}/send-setup-email", headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["sent"] is True and data["email"] == "john@company.com"
    assert data["link"] == f"https://sig.test/setup/{setup.setup_key(john.id)}"

    msg = smtp.sent[0]
    assert msg["To"] == "john@company.com" and "email signature is ready" in msg["Subject"]
    html = msg.get_body(("html",)).get_content()
    assert "Set up my signature" in html and data["link"] in html
    assert "John Smith" in html and "/static/brand/casterly-logo.png" in html  # signature with images
    assert data["link"] in msg.get_body(("plain",)).get_content()


def test_send_email_is_audited(client, admin_headers, template, john, smtp):
    client.post(f"/api/signatures/{john.id}/send-setup-email", headers=admin_headers)
    items = client.get("/api/audit-logs?action=SIGNATURE_SETUP_EMAIL_SENT", headers=admin_headers).json()["data"]["items"]
    assert items and "john@company.com" in items[0]["description"]


def test_without_smtp_the_app_reports_it_and_offers_the_link(client, admin_headers, template, john):
    r = client.post(f"/api/signatures/{john.id}/send-setup-email", headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "EMAIL_NOT_CONFIGURED"
    link = client.get(f"/api/signatures/{john.id}/setup-link", headers=admin_headers).json()["data"]
    assert link["email_configured"] is False and link["link"].startswith("https://sig.test/setup/")
    assert f'href="{link["link"]}"' in link["email_html"] and "Set up my signature" in link["email_html"]
    assert "John Smith" in link["email_html"] and "<html" not in link["email_html"]


def test_only_admins_can_send(client, john_headers, john, smtp):
    assert client.post(f"/api/signatures/{john.id}/send-setup-email", headers=john_headers).status_code == 403
    assert client.get(f"/api/signatures/{john.id}/setup-link", headers=john_headers).status_code == 403


def test_inactive_employee_cannot_be_sent(client, db, admin_headers, template, john, smtp):
    john.is_active = False
    db.commit()
    r = client.post(f"/api/signatures/{john.id}/send-setup-email", headers=admin_headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "EMPLOYEE_INACTIVE"
    assert smtp.sent == []


def test_setup_page_shows_signature_and_all_options(client, template, john):
    key = setup.setup_key(john.id)
    r = client.get(f"/setup/{key}")  # no login
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    page = r.text
    assert "John Smith" in page and "/banner/current.png" in page
    # New Outlook / web: download the manifest and add it from the file - never "Add from URL".
    assert 'href="https://sig.test/outlook-addin/manifest.xml?download=true"' in page
    assert "Download Outlook Add-in Manifest" in page
    for step in ("My Add-ins", "Add a custom add-in", "Add from File", "casterly-signatures-manifest.xml", "Install"):
        assert step in page, step
    assert "Add from URL" not in page and "Copy address" not in page
    assert "Insert Casterly signature" in page  # manual fallback is mentioned
    # Classic Outlook: the per-employee installer.
    assert f'href="https://sig.test/setup/{key}/installer"' in page and "Download Outlook Installer" in page
    assert "Restart Outlook" in page
    # Any other app: copy, or the separately labelled HTML download. Never a PDF.
    assert "Copy signature" in page and "Download Signature HTML" in page
    assert f'href="https://sig.test/setup/{key}/signature.html"' in page
    assert "pdf" not in page.lower()


def test_setup_page_hides_the_add_in_when_outlook_cannot_load_it(client, monkeypatch, template, john):
    monkeypatch.setattr(get_settings(), "public_base_url", "http://192.168.0.190")
    page = client.get(f"/setup/{setup.setup_key(john.id)}").text
    assert "manifest.xml" not in page and "isn't available yet" in page
    assert "Download Outlook Installer" in page  # classic Outlook still works over plain http


def test_setup_signature_html_download(client, template, john, priya):
    key = setup.setup_key(john.id)
    r = client.get(f"/setup/{key}/signature.html")  # no login, only with the personal key
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert r.headers["content-disposition"] == f'attachment; filename="{john.employee_code}-signature.html"'
    assert r.text.startswith("<!DOCTYPE html>") and "John Smith" in r.text and "/banner/current.png" in r.text
    forged = f"{priya.id}.{key.split('.', 1)[1]}"
    assert client.get(f"/setup/{forged}/signature.html").status_code == 404


def test_setup_page_rejects_bad_links(client, template, john, priya):
    assert client.get("/setup/garbage").status_code == 404
    priya_key = setup.setup_key(priya.id)
    forged = f"{john.id}.{priya_key.split('.', 1)[1]}"
    assert client.get(f"/setup/{forged}").status_code == 404


def test_setup_installer_download(client, tmp_path, monkeypatch, john):
    from app import installer

    exe = tmp_path / "setup.exe"
    exe.write_bytes(b"MZ")
    monkeypatch.setattr(installer, "INSTALLER_FILE", exe)
    r = client.get(f"/setup/{setup.setup_key(john.id)}/installer")
    assert r.status_code == 200 and r.content == b"MZ"
    assert installer.installer_filename(john.id) in r.headers["content-disposition"]
