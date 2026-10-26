"""Outlook add-in: manifest, runtime files, signature by email, and the public gateway."""
import re
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from app.database.database import get_db
from app.public_app import app as public_app
from tests.conftest import create_banner, publish

NS = {"o": "http://schemas.microsoft.com/office/appforoffice/1.1"}
VO = "{http://schemas.microsoft.com/office/mailappversionoverrides/1.1}"
BT = "{http://schemas.microsoft.com/office/officeappbasictypes/1.0}"
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"


def test_manifest_is_valid_xml_with_public_https_style_urls(client):
    r = client.get("/outlook-addin/manifest.xml")
    assert r.status_code == 200 and "xml" in r.headers["content-type"]
    root = ET.fromstring(r.content)
    assert root.find("o:Id", NS).text == "3c2fd8a4-20c3-4340-98ad-515e118a4626"
    assert root.find("o:DisplayName", NS).get("DefaultValue") == "Casterly Signatures"
    text = r.text
    assert 'LaunchEvent Type="OnNewMessageCompose" FunctionName="onNewMessageComposeHandler"' in text
    assert "https://sig.test/outlook-addin/commands.html" in text
    assert "https://sig.test/outlook-addin/launchevent.js" in text
    assert "localhost" not in text
    r = client.get("/outlook-addin/manifest.xml?download=true")
    assert "attachment" in r.headers["content-disposition"]


def test_every_manifest_url_uses_the_public_https_base(client):
    text = client.get("/outlook-addin/manifest.xml").text
    urls = set(re.findall(r'"(https?://[^"]+)"', text)) | set(re.findall(r">(https?://[^<]+)<", text))
    urls = {u for u in urls if not u.startswith(("http://schemas.microsoft.com/", "http://www.w3.org/"))}
    assert urls  # manifest, runtime pages, icons
    assert all(u == "https://sig.test" or u.startswith("https://sig.test/") for u in urls), urls
    paths = {u.removeprefix("https://sig.test") for u in urls}
    assert {"/outlook-addin/commands.html", "/outlook-addin/launchevent.js"} <= paths
    for path in paths - {""}:  # every file the manifest points at is served
        assert client.get(path).status_code == 200, path
    assert "trycloudflare" not in text


def test_manifest_meets_outlook_requirements(client):
    root = ET.fromstring(client.get("/outlook-addin/manifest.xml").content)
    assert root.get(XSI_TYPE) == "MailApp"
    assert re.fullmatch(r"\d{1,5}(\.\d{1,5}){3}", root.find("o:Version", NS).text)
    assert [h.get("Name") for h in root.find("o:Hosts", NS)] == ["Mailbox"]
    assert root.find("o:Requirements/o:Sets/o:Set", NS).get("Name") == "Mailbox"
    assert root.find("o:Permissions", NS).text == "ReadWriteItem"
    outer = "{http://schemas.microsoft.com/office/mailappversionoverrides}VersionOverrides"
    overrides = root.find(f"{outer}/{VO}VersionOverrides")
    assert overrides.get(XSI_TYPE) == "VersionOverridesV1_1"
    # setSignatureAsync and LaunchEvent need Mailbox 1.10.
    assert overrides.find(f"{VO}Requirements/{BT}Sets").get("DefaultMinVersion") == "1.10"
    desktop = overrides.find(f"{VO}Hosts/{VO}Host/{VO}DesktopFormFactor")
    points = {p.get(XSI_TYPE): p for p in desktop.findall(f"{VO}ExtensionPoint")}
    event = points["LaunchEvent"].find(f"{VO}LaunchEvents/{VO}LaunchEvent")
    assert (event.get("Type"), event.get("FunctionName")) == ("OnNewMessageCompose", "onNewMessageComposeHandler")
    button = points["MessageComposeCommandSurface"].find(f".//{VO}Control")
    assert button.find(f"{VO}Action/{VO}FunctionName").text == "insertCasterlySignature"
    # Every resid used in the manifest is defined in Resources.
    defined = {el.get("id") for el in overrides.find(f"{VO}Resources").iter() if el.get("id")}
    used = {el.get("resid") for el in overrides.iter() if el.get("resid")}
    assert used <= defined, used - defined
    # new Outlook / web run commands.html; classic Outlook runs launchevent.js.
    runtime = overrides.find(f"{VO}Hosts/{VO}Host/{VO}Runtimes/{VO}Runtime")
    assert runtime.get("resid") == "WebViewRuntime.Url"
    assert runtime.find(f"{VO}Override").get("type") == "javascript"


def test_manifest_downloads_as_a_file_for_add_from_file(client):
    r = client.get("/outlook-addin/manifest.xml?download=true")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/xml")
    assert r.headers["content-disposition"] == 'attachment; filename="casterly-signatures-manifest.xml"'
    assert "no-cache" in r.headers["cache-control"]
    ET.fromstring(r.content)


def test_runtime_files_point_at_this_server(client):
    js = client.get("/outlook-addin/launchevent.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert 'Office.actions.associate("onNewMessageComposeHandler"' in js.text
    assert "https://sig.test/api/outlook/signature" in js.text
    assert "setSignatureAsync(" in js.text and "isClientSignatureEnabledAsync" in js.text
    assert "disableClientSignatureAsync(" not in js.text  # never force Outlook to "no signature"
    page = client.get("/outlook-addin/commands.html")
    assert "office.js" in page.text and "https://sig.test/outlook-addin/launchevent.js" in page.text


def test_icons_exist(client):
    for size in (16, 32, 64, 80, 128):
        assert client.get(f"/static/brand/icon-{size}.png").status_code == 200


def test_signature_by_email_is_fresh_on_every_call(client, admin_headers, template, john):
    r = client.get("/api/outlook/signature?email=JOHN@company.com")  # case-insensitive, no login
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "John Smith" in r.text and "/banner/current.png" in r.text
    assert r.headers["cache-control"] == "no-store"
    # Change the employee's details: the very next email gets them.
    client.patch(f"/api/employees/{john.id}/status", json={"is_active": True}, headers=admin_headers)
    a = create_banner(client, admin_headers, "Launch")
    publish(client, admin_headers, a["id"])
    assert client.get("/api/outlook/signature?email=john@company.com").status_code == 200


def test_signature_by_email_unknown_or_inactive(client, db, template, john):
    assert client.get("/api/outlook/signature?email=nobody@company.com").status_code == 404
    john.is_active = False
    db.commit()
    r = client.get("/api/outlook/signature?email=john@company.com")
    assert r.status_code == 404 and r.json()["error"]["code"] == "EMPLOYEE_NOT_FOUND"


# --------------------------------------------------------------- gateway --
@pytest.fixture
def gateway(engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    public_app.dependency_overrides[get_db] = _get_db
    with TestClient(public_app) as c:
        yield c
    public_app.dependency_overrides.clear()


def test_gateway_serves_only_public_routes(gateway, template, john):
    assert gateway.get("/outlook-addin/manifest.xml").status_code == 200
    assert gateway.get("/outlook-addin/launchevent.js").status_code == 200
    assert gateway.get("/api/outlook/signature?email=john@company.com").status_code == 200
    assert gateway.get("/banner/current.png").status_code == 200
    assert gateway.get("/static/brand/casterly-logo.png").status_code == 200
    # Nothing that needs (or could brute-force) a login is exposed.
    for path in ("/api/auth/login", "/api/employees", "/api/banners", "/api/settings", "/api/docs", "/api/openapi.json"):
        assert gateway.get(path).status_code == 404, path
    assert gateway.post("/api/auth/login", json={"email": "a@b.c", "password": "x"}).status_code in (404, 405)


def test_manifest_version_changes_with_the_server_address():
    from app.api.outlook_addin import addin_version, manifest_xml

    a, b = addin_version("https://one.example"), addin_version("https://two.example")
    assert a != b and a == addin_version("https://one.example")
    parts = a.split(".")
    assert len(parts) == 4 and all(0 <= int(x) <= 65535 for x in parts)
    assert f"<Version>{a}</Version>" in manifest_xml("https://one.example")


def test_manifest_version_changes_with_the_manifest_content(monkeypatch):
    from app.api import outlook_addin

    before = outlook_addin.addin_version("https://one.example")
    template = outlook_addin._manifest_template
    monkeypatch.setattr(outlook_addin, "_manifest_template", lambda base: template(base).replace(
        "Insert Casterly signature", "Insert signature"))
    assert outlook_addin.addin_version("https://one.example") != before


def test_public_url_checks():
    from app.utils.urls import outlook_url_problem

    assert outlook_url_problem("https://signatures.casterly.com") is None
    assert outlook_url_problem("https://localhost:8443") is None  # testing on this PC with the dev certificate
    for bad in ("http://signatures.casterly.com", "http://192.168.0.190/signature", "http://localhost:8001",
                "https://192.168.0.190", "https://box.local"):
        assert outlook_url_problem(bad), bad


def test_quick_tunnel_addresses_work_but_are_flagged():
    from app.core.config import Settings
    from app.utils.urls import is_temporary_tunnel, outlook_url_problem

    tunnel = "https://day-div-randy-deals.trycloudflare.com"
    assert Settings(secret_key="x" * 32, public_base_url=tunnel + "/").public_base_url == tunnel
    assert outlook_url_problem(tunnel) is None and is_temporary_tunnel(tunnel)
    assert not is_temporary_tunnel("https://signatures.casterly.com")
