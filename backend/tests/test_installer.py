"""Outlook installer: personal download, key-protected signature fetch, live banner URLs."""
import base64
import io
import re

import pytest
from PIL import Image

from app import installer
from tests.conftest import create_banner, publish


def _png(color=(200, 30, 30), size=(1200, 240)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def fake_exe(tmp_path, monkeypatch):
    exe = tmp_path / "CasterlySignatureSetup.exe"
    exe.write_bytes(b"MZ-test-installer")
    monkeypatch.setattr(installer, "INSTALLER_FILE", exe)
    return exe


def _key_from(disposition: str) -> tuple[str, int, str]:
    name = re.search(r'filename="([^"]+)"', disposition).group(1)
    assert name.startswith("Casterly-Signature-Setup_") and name.endswith(".exe")
    server_b64, eid, sig = name.removeprefix("Casterly-Signature-Setup_").removesuffix(".exe").split(".")
    server = base64.urlsafe_b64decode(server_b64 + "=" * (-len(server_b64) % 4)).decode()
    return server, int(eid), sig


# ------------------------------------------------------------- download --
def test_employee_downloads_their_personal_installer(client, fake_exe, john, john_headers):
    r = client.get("/api/signatures/me/installer", headers=john_headers)
    assert r.status_code == 200
    assert r.content == fake_exe.read_bytes()  # same program for everyone
    server, eid, sig = _key_from(r.headers["content-disposition"])
    assert server == "https://sig.test" and eid == john.id and installer.verify_key(john.id, sig)


def test_admin_can_download_for_any_employee(client, fake_exe, admin_headers, priya):
    r = client.get(f"/api/signatures/{priya.id}/installer", headers=admin_headers)
    assert r.status_code == 200
    assert _key_from(r.headers["content-disposition"])[1] == priya.id


def test_employee_cannot_download_someone_elses_installer(client, fake_exe, john_headers, priya):
    assert client.get(f"/api/signatures/{priya.id}/installer", headers=john_headers).status_code == 403


def test_download_requires_login(client, fake_exe, john):
    assert client.get(f"/api/signatures/{john.id}/installer").status_code == 401


def test_missing_installer_build_is_reported(client, tmp_path, monkeypatch, john_headers):
    monkeypatch.setattr(installer, "INSTALLER_FILE", tmp_path / "missing.exe")
    r = client.get("/api/signatures/me/installer", headers=john_headers)
    assert r.status_code == 503 and r.json()["error"]["code"] == "INSTALLER_UNAVAILABLE"


def test_download_is_audited(client, fake_exe, admin_headers, john, john_headers):
    client.get("/api/signatures/me/installer", headers=john_headers)
    items = client.get("/api/audit-logs?action=SIGNATURE_INSTALLER_DOWNLOADED", headers=admin_headers).json()["data"]["items"]
    assert items and "John Smith" in items[0]["description"]


# ---------------------------------------------------- signature for exe --
def test_installer_fetches_live_signature_with_valid_key(client, admin_headers, template, john):
    sig = installer.employee_key_signature(john.id)
    r = client.get(f"/api/installer/signature?e={john.id}&s={sig}")  # no login: the key is the credential
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["signature_name"] == "Casterly signature" and data["employee_name"] == "John Smith"
    html = data["html"]
    assert "John Smith" in html and "john@company.com" in html
    # Live banner addresses, not a specific banner, so it never needs reinstalling.
    assert 'src="https://sig.test/banner/current.png"' in html
    assert 'href="https://sig.test/banner/current"' in html
    assert "/static/brand/casterly-logo.png" in html  # logo is on by default
    assert "John Smith" in data["text"] and "<" not in data["text"]


def test_installer_rejects_bad_or_reused_keys(client, template, john, priya):
    assert client.get(f"/api/installer/signature?e={john.id}&s=wrong").status_code == 403
    johns_key = installer.employee_key_signature(john.id)
    r = client.get(f"/api/installer/signature?e={priya.id}&s={johns_key}")  # John's key for Priya
    assert r.status_code == 403 and r.json()["error"]["code"] == "INVALID_INSTALLER_KEY"


def test_installer_refuses_inactive_employees(client, db, template, john):
    john.is_active = False
    db.commit()
    r = client.get(f"/api/installer/signature?e={john.id}&s={installer.employee_key_signature(john.id)}")
    assert r.status_code == 403 and r.json()["error"]["code"] == "EMPLOYEE_INACTIVE"


def test_installation_is_audited(client, admin_headers, template, john):
    client.get(f"/api/installer/signature?e={john.id}&s={installer.employee_key_signature(john.id)}")
    items = client.get("/api/audit-logs?action=SIGNATURE_INSTALLED", headers=admin_headers).json()["data"]["items"]
    assert items and items[0]["user_email"] == "john@company.com"


# ------------------------------------------------------- live banner URLs --
def test_live_banner_follows_publishing(client, admin_headers):
    # Nothing published: an invisible 1200x2 strip.
    r = client.get("/banner/current.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(r.content)).size == (1200, 2)
    assert "no-cache" in r.headers["cache-control"]

    red = client.post("/api/uploads", data={"kind": "banner"}, files={"file": ("a.png", _png((200, 0, 0)), "image/png")},
                      headers=admin_headers).json()["data"]["path"]
    blue = client.post("/api/uploads", data={"kind": "banner"}, files={"file": ("b.png", _png((0, 0, 200)), "image/png")},
                       headers=admin_headers).json()["data"]["path"]
    a = create_banner(client, admin_headers, "A", image_url=red, target_url="https://casterly.example/a")
    b = create_banner(client, admin_headers, "B", image_url=blue, target_url="https://casterly.example/b")

    publish(client, admin_headers, a["id"])
    assert client.get("/banner/current.png").content == _png((200, 0, 0))
    r = client.get("/banner/current", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "https://casterly.example/a"

    publish(client, admin_headers, b["id"])  # same URLs now show banner B
    assert client.get("/banner/current.png").content == _png((0, 0, 200))
    assert client.get("/banner/current", follow_redirects=False).headers["location"] == "https://casterly.example/b"

    client.post(f"/api/banners/{b['id']}/unpublish", headers=admin_headers)
    assert Image.open(io.BytesIO(client.get("/banner/current.png").content)).size == (1200, 2)


def test_live_banner_redirects_to_external_image(client, admin_headers):
    a = create_banner(client, admin_headers, "Ext", image_url="https://cdn.example.com/banner.png")
    publish(client, admin_headers, a["id"])
    r = client.get("/banner/current.png", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "https://cdn.example.com/banner.png"


def test_live_banner_link_without_banner(client, admin_headers):
    r = client.get("/banner/current", follow_redirects=False)
    assert r.status_code == 200 and "no current campaign" in r.text.lower()
    client.put("/api/settings", json={"company_name": "Casterly Private Limited", "company_website": "casterly.example"},
               headers=admin_headers)
    r = client.get("/banner/current", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "https://casterly.example"


def test_regular_signatures_still_use_the_specific_banner(client, admin_headers, template, john):
    a = create_banner(client, admin_headers, "Launch")
    publish(client, admin_headers, a["id"])
    html = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]["html"]
    assert "launch.png" in html and "/banner/current.png" not in html


# ---------------------------------------------- paste-once (new Outlook) --
def test_copy_version_uses_the_live_banner(client, admin_headers, template, john):
    a = create_banner(client, admin_headers, "Launch")
    publish(client, admin_headers, a["id"])
    data = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]
    assert "launch.png" in data["html"]  # preview shows today's banner
    live = data["live_html"]
    assert 'src="https://sig.test/banner/current.png"' in live and "launch.png" not in live
    assert "John Smith" in live and "/static/brand/casterly-logo.png" in live


def test_html_endpoint_can_return_the_live_version(client, admin_headers, template, john):
    a = create_banner(client, admin_headers, "Launch")
    publish(client, admin_headers, a["id"])
    assert "launch.png" in client.get(f"/api/signatures/{john.id}/html", headers=admin_headers).text
    live = client.get(f"/api/signatures/{john.id}/html?live=true&download=true", headers=admin_headers)
    assert "/banner/current.png" in live.text and "launch.png" not in live.text
    assert "attachment" in live.headers["content-disposition"]
