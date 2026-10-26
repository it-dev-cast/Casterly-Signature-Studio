"""Employee address: comes only from nexusAuth, is read-only here, and shows smaller in the signature."""
from app.database.models import Employee, SignatureTemplate
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


def test_office_addresses_are_shown_in_full_and_smaller(client, db, admin_headers, template):
    emp = create(client, admin_headers, profile_photo_url="/uploads/photos/a.jpg")  # narrowest column
    for address in (TOWERS, B8):
        set_address_from_nexus(db, emp["id"], address)
        html = signature(client, admin_headers, emp["id"])
        assert address in html  # never shortened
        cell = html[html.rindex("<td", 0, html.index(address)):html.index(address)]
        assert "font-size:10px" in cell and "line-height:13px" in cell
        assert "font-size:11px" in html  # contact lines keep their size


def test_long_custom_address_is_kept_to_two_lines(client, db, admin_headers, template):
    emp = create(client, admin_headers)
    set_address_from_nexus(db, emp["id"], "Brigade Twin Towers, Tower B, 14th Floor, " * 6)
    html = signature(client, admin_headers, emp["id"])
    shown = html[html.index("Brigade Twin Towers"):html.index("</td>", html.index("Brigade Twin Towers"))]
    assert shown.endswith("…") and len(shown) <= 150  # ~2 lines of the address column, never 3+


def test_address_in_minimal_layout_is_small_and_escaped(client, db, admin_headers, template):
    db.add(SignatureTemplate(name="Minimal", layout="minimal"))
    db.commit()
    minimal_id = db.query(SignatureTemplate).filter_by(name="Minimal").one().id
    emp = create(client, admin_headers)
    set_address_from_nexus(db, emp["id"], "<b>HQ</b> & Co")
    html = signature(client, admin_headers, emp["id"], template_id=minimal_id)
    assert "&lt;b&gt;HQ&lt;/b&gt; &amp; Co" in html and "<b>HQ</b>" not in html
    assert "font-size:10px" in html


def test_no_address_row_without_an_address(client, admin_headers, template):
    emp = create(client, admin_headers)
    assert ">A&nbsp;</td>" not in signature(client, admin_headers, emp["id"])
