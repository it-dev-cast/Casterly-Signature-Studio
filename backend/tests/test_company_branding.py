"""Built-in company logo: always available, shown in a 50x50 slot at the top-right of the
employee details (just above the banner), with only an on/off switch in Settings."""
import re

from app import branding
from tests.conftest import create_banner, publish

SETTINGS = {"company_name": "Casterly Private Limited", "company_website": None, "legal_disclaimer": None}
LOGO_SRC = "https://sig.test/static/brand/casterly-logo.png"  # in emails
LOGO_PATH = "/static/brand/casterly-logo.png"  # in the app


def _html(client, headers, employee_id, query=""):
    r = client.get(f"/api/signatures/{employee_id}{query}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]["html"]


def _set(client, headers, **overrides):
    r = client.put("/api/settings", json={**SETTINGS, **overrides}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_logo_file_is_bundled_and_served(client):
    assert branding.LOGO_FILE.is_file()
    r = client.get(branding.LOGO_PATH)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_logo_is_on_by_default(client, admin_headers, template, john):
    data = client.get("/api/settings", headers=admin_headers).json()["data"]
    assert data["show_logo_in_signature"] is True
    assert data["company_logo_url"] == LOGO_PATH
    assert f'src="{LOGO_SRC}"' in _html(client, admin_headers, john.id)


def test_logo_sits_right_aligned_just_above_the_banner(client, admin_headers, template, john):
    _set(client, admin_headers)
    banner = create_banner(client, admin_headers, "Launch")
    publish(client, admin_headers, banner["id"])
    html = _html(client, admin_headers, john.id)

    w, h = branding.logo_display_size()
    assert (w, h) == (32, 50)  # 501x772 fitted into a 50x50 box, aspect ratio kept
    logo_tag = f'<img src="{LOGO_SRC}" alt="Casterly Private Limited" width="{w}" height="{h}"'
    assert logo_tag in html
    # In a fixed 50x50 box, top-right of the details row...
    assert (f'<td valign="top" align="right" width="50" height="50" '
            f'style="padding:0;width:50px;height:50px;">{logo_tag}') in html
    assert html.index('<td valign="top" align="right" width="50" style="padding:0;width:50px;">') < html.index(logo_tag)
    # ...and that row is immediately followed by the banner row.
    assert re.search(re.escape(logo_tag) + r'[^<]*</td></tr></table></td></tr><tr><td colspan="\d" [^>]*><table[^>]*><tr><td[^>]*><a[^>]*><img src="[^"]*launch\.png"', html)
    # The signature is banner-wide, so the logo lines up with the banner's right edge.
    assert html.startswith('<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="480"')


def test_logo_above_banner_in_minimal_layout(client, db, admin_headers, john):
    from app.database.models import SignatureTemplate

    minimal = SignatureTemplate(name="Min", layout="minimal", is_active=True)
    db.add(minimal)
    db.commit()
    banner = create_banner(client, admin_headers, "Launch")
    publish(client, admin_headers, banner["id"])
    html = _html(client, admin_headers, john.id)
    logo_at, banner_at = html.index(LOGO_SRC), html.index("launch.png")
    assert logo_at < banner_at
    assert f'<td align="right" style="padding:6px 0 0 0;"><img src="{LOGO_SRC}"' in html


def test_logo_shown_even_without_a_banner(client, admin_headers, template, john):
    assert LOGO_SRC in _html(client, admin_headers, john.id)


def test_switching_the_logo_off_and_on(client, admin_headers, template, john, priya):
    data = _set(client, admin_headers, show_logo_in_signature=False)
    assert data["show_logo_in_signature"] is False
    for emp in (john, priya):
        html = _html(client, admin_headers, emp.id)
        assert LOGO_SRC not in html
        assert 'width="480"' not in html.split(">", 1)[0]  # back to the compact layout
    _set(client, admin_headers, show_logo_in_signature=True)
    for emp in (john, priya):
        assert LOGO_SRC in _html(client, admin_headers, emp.id)


def test_toggle_is_audited(client, admin_headers):
    _set(client, admin_headers, show_logo_in_signature=False)
    items = client.get("/api/audit-logs?action=SETTINGS_UPDATED", headers=admin_headers).json()["data"]["items"]
    assert "company logo in signatures turned off" in items[0]["description"]


def test_logo_cannot_be_changed_through_the_api(client, admin_headers, template, john):
    r = client.put("/api/settings", json={**SETTINGS, "company_logo_url": "https://evil.example/logo.png"},
                   headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["company_logo_url"] == LOGO_PATH
    assert "evil.example" not in _html(client, admin_headers, john.id)
    r = client.post("/api/uploads", data={"kind": "logo"}, files={"file": ("l.png", b"x", "image/png")},
                    headers=admin_headers)
    assert r.status_code == 422


def test_branding_is_public(client, admin_headers):
    _set(client, admin_headers)
    r = client.get("/api/branding")  # no auth header
    assert r.status_code == 200
    assert r.json()["data"] == {"company_name": "Casterly Private Limited", "company_logo_url": LOGO_PATH,
                                "public_base_url": "https://sig.test"}


def test_settings_require_admin(client, john_headers):
    assert client.put("/api/settings", json=SETTINGS, headers=john_headers).status_code == 403
