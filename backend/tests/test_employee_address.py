"""Employee address: comes only from nexusAuth, is read-only here, and shows smaller in the signature."""
import re

import pytest

from app.database.models import Employee, SignatureTemplate
from tests.conftest import create_banner, publish, stored_image
from tests.test_employees import PAYLOAD

# The two office addresses offered in nexusAuth's address dropdown.
TOWERS = "Tower B Beacon, 4th Floor, Brigade Twin Towers, Pipeline Road, Yeshwanthpur, Bengaluru, Karnataka 560022"
B8 = ("B-8, Ragavendra Layout, Jai Bharath Industrial Estate, Yeshwanthpur, Bengaluru, Bengaluru Urban, "
      "Karnataka, 560022.")


def create(client, headers, **extra):
    r = client.post("/api/employees", json={**PAYLOAD, **extra}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["data"]


def set_address_from_nexus(db, employee_id, address):
    """What the nexusAuth sync does (see test_nexus_sync for the sync itself)."""
    emp = db.get(Employee, employee_id)
    emp.address = address
    db.commit()


def signature(client, headers, employee_id, **params):
    return client.get(f"/api/signatures/{employee_id}", params=params, headers=headers).json()["data"]["html"]


def test_address_cannot_be_set_or_changed_in_signature_studio(client, db, admin_headers):
    emp = create(client, admin_headers, address="Typed in Signature Studio")
    assert emp["address"] is None  # ignored on create
    set_address_from_nexus(db, emp["id"], TOWERS)
    r = client.put(f"/api/employees/{emp['id']}", json={**PAYLOAD, "address": "Changed here"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["data"]["address"] == TOWERS  # an edit here never changes it


def test_address_is_returned_for_display(client, db, admin_headers):
    emp = create(client, admin_headers)
    set_address_from_nexus(db, emp["id"], B8)
    assert client.get(f"/api/employees/{emp['id']}", headers=admin_headers).json()["data"]["address"] == B8


def test_multi_line_address_appears_on_one_line(client, db, admin_headers, template):
    emp = create(client, admin_headers)
    set_address_from_nexus(db, emp["id"], "No. 12, 2nd Floor, MG Road\nBengaluru 560001")
    assert "No. 12, 2nd Floor, MG Road, Bengaluru 560001" in signature(client, admin_headers, emp["id"])


def _address_cell(html: str, address: str) -> str:
    """The opening <td ...> of the cell holding the address."""
    at = html.index(address)
    return html[html.rindex("<td", 0, at):at]


@pytest.mark.parametrize("with_banner", [True, False])
def test_office_addresses_are_shown_in_full_in_dark_11px_text(client, db, admin_headers, template, with_banner):
    if with_banner:
        publish(client, admin_headers, create_banner(client, admin_headers)["id"])
    photo = stored_image("photos/a.jpg", (256, 256), "JPEG")
    emp = create(client, admin_headers, profile_photo_url=photo)  # narrowest column
    for address in (TOWERS, B8):
        set_address_from_nexus(db, emp["id"], address)
        html = signature(client, admin_headers, emp["id"])
        assert address in html  # never shortened: it wraps to a second line instead
        cell = _address_cell(html, address)
        assert "font-size:11px" in cell and "line-height:15px" in cell and "color:#374151" in cell


def test_office_addresses_fit_two_lines_of_the_banner_width():
    # 11px Arial (the signature's font): each preset address wraps to two lines at most.
    from PIL import ImageFont

    from app.renderers.banner import BANNER_WIDTH
    from app.renderers.classic import ADDRESS_SIZE

    try:
        font = ImageFont.truetype("arial.ttf", ADDRESS_SIZE * 4)  # measured at 4x for precision
    except OSError:
        pytest.skip("Arial is not installed")
    for address in (TOWERS, B8):
        assert BANNER_WIDTH < font.getlength(address) / 4 <= 2 * BANNER_WIDTH, address


def test_address_up_to_two_lines_is_never_shortened(client, db, admin_headers, template):
    publish(client, admin_headers, create_banner(client, admin_headers)["id"])
    emp = create(client, admin_headers)
    address = "Unit 7, " + "Brigade Twin Towers, " * 7 + "Bengaluru 560022"  # 171 chars: ~1.8 lines at 11px
    set_address_from_nexus(db, emp["id"], address)
    assert address in signature(client, admin_headers, emp["id"])


@pytest.mark.parametrize("with_banner,max_chars", [(True, 190), (False, 165)])
def test_address_longer_than_two_lines_is_shortened(client, db, admin_headers, template, with_banner, max_chars):
    if with_banner:  # under the 480px banner; without one, in the narrower details column
        publish(client, admin_headers, create_banner(client, admin_headers)["id"])
    emp = create(client, admin_headers)
    set_address_from_nexus(db, emp["id"], "Brigade Twin Towers, Tower B, 14th Floor, " * 7)  # 294 of the 300 allowed
    html = signature(client, admin_headers, emp["id"])
    shown = html[html.index("Brigade Twin Towers"):html.index("</td>", html.index("Brigade Twin Towers"))]
    assert shown.endswith("…") and len(shown) <= max_chars  # ~2 lines at 11px, never 3+


def test_address_in_minimal_layout_is_small_and_escaped(client, db, admin_headers, template):
    db.add(SignatureTemplate(name="Minimal", layout="minimal"))
    db.commit()
    minimal_id = db.query(SignatureTemplate).filter_by(name="Minimal").one().id
    emp = create(client, admin_headers)
    set_address_from_nexus(db, emp["id"], "<b>HQ</b> & Co")
    html = signature(client, admin_headers, emp["id"], template_id=minimal_id)
    assert "&lt;b&gt;HQ&lt;/b&gt; &amp; Co" in html and "<b>HQ</b>" not in html
    assert "font-size:10px" in html


def test_no_address_line_without_an_address(client, admin_headers, template):
    emp = create(client, admin_headers)
    html = signature(client, admin_headers, emp["id"])
    assert html.count("padding:4px 0 0 0;") == 1  # only the social links row under the contacts
    publish(client, admin_headers, create_banner(client, admin_headers)["id"])
    html = signature(client, admin_headers, emp["id"])
    assert "<tr" not in html[html.index("banners/banner-a.png"):]  # nothing after the banner
    assert 'height="4"' not in html and ">A&nbsp;</td>" not in html


# ------------------------------------------------ where the address is shown --
def _contact_labels(html: str) -> list[str]:
    return re.findall(r'font-weight:bold;color:#[0-9A-Fa-f]{6};">([A-Z])&nbsp;</td>', html)


def test_contact_rows_are_only_p_e_w_and_the_address_has_no_label(client, db, admin_headers, template):
    emp = create(client, admin_headers)
    set_address_from_nexus(db, emp["id"], TOWERS)
    html = signature(client, admin_headers, emp["id"])
    assert _contact_labels(html) == ["P", "E", "W"]
    assert ">A&nbsp;</td>" not in html
    assert _address_cell(html, TOWERS).rstrip().endswith(">")  # the text starts right after the cell


def test_address_is_below_the_banner_left_aligned_with_a_small_gap(client, db, admin_headers, template):
    client.put("/api/settings", headers=admin_headers, json={
        "company_name": "Casterly Private Limited", "company_website": None, "legal_disclaimer": "Confidential."})
    publish(client, admin_headers, create_banner(client, admin_headers)["id"])
    emp = create(client, admin_headers)
    set_address_from_nexus(db, emp["id"], TOWERS)
    html = signature(client, admin_headers, emp["id"])
    banner_at, address_at = html.index("banners/banner-a.png"), html.index(TOWERS)
    assert html.index("rahul@example.com") < banner_at < address_at < html.index("Confidential.")
    cell = _address_cell(html, TOWERS)
    assert 'colspan="' in cell and "padding:0;" in cell  # full width, left edge in line with the banner
    between = html[html.index("</table>", banner_at):address_at]
    assert 'height="4"' in between and "line-height:4px" in between  # the small gap: a spacer row


def test_without_a_banner_the_address_follows_the_contact_lines(client, db, admin_headers, template):
    emp = create(client, admin_headers)
    set_address_from_nexus(db, emp["id"], TOWERS)
    html = signature(client, admin_headers, emp["id"])
    assert "banners/" not in html
    assert html.index("example.com</a>") < html.index(TOWERS) < html.index("LinkedIn")  # after W, before social
    assert 'colspan="' not in _address_cell(html, TOWERS)  # inside the details column


def test_saved_installer_addin_and_html_outputs_put_the_address_under_the_banner(client, db, admin_headers, template):
    from app import installer

    publish(client, admin_headers, create_banner(client, admin_headers)["id"])
    emp = create(client, admin_headers)
    set_address_from_nexus(db, emp["id"], TOWERS)
    data = client.get(f"/api/signatures/{emp['id']}", headers=admin_headers).json()["data"]
    raw = client.get(f"/api/signatures/{emp['id']}/html", headers=admin_headers).text  # copy / HTML output
    addin = client.get("/api/outlook/signature", params={"email": "rahul@example.com"}).text
    key = installer.employee_key_signature(emp["id"])
    saved = client.get("/api/installer/signature", params={"e": emp["id"], "s": key}).json()["data"]["html"]
    for html, banner in ((raw, "banners/banner-a.png"), (data["live_html"], "/banner/current.png"),
                         (addin, "/banner/current.png?v="), (saved, "/banner/current.png")):
        assert html.index(banner) < html.index(TOWERS), banner
        assert _contact_labels(html) == ["P", "E", "W"]
