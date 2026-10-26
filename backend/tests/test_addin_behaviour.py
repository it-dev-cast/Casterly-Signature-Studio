"""Runs the REAL add-in script (launchevent.js) in Node against a stand-in Office.js.

Checks the end-to-end behaviour the employee sees in Outlook: the signed-in user's own
signature, inserted once, always the latest version, never forcing "No signature".
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.database.models import Employee
from tests.conftest import create_banner, make_employee, publish

HARNESS = Path(__file__).parent / "js" / "addin_harness.js"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is needed to run the add-in script")

SETTINGS = {"company_name": "Casterly Private Limited", "company_website": None, "legal_disclaimer": None}


def _sig(client, email):
    r = client.get("/api/outlook/signature", params={"email": email})
    return {"status": r.status_code, "html": r.text if r.status_code == 200 else "",
            "mode": r.headers.get("x-casterly-signature-mode")}


def run(client, user, composes=("auto",), outlook_default=False, emails=None):
    emails = emails or [user["email"]]
    cfg = {
        "script": client.get("/outlook-addin/launchevent.js").text,
        "user": user,
        "outlookDefault": outlook_default,
        "signatures": {e: _sig(client, e) for e in emails},
        "composes": list(composes),
    }
    out = subprocess.run(["node", str(HARNESS)], input=json.dumps(cfg), capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@pytest.fixture
def rajatha(db):
    return make_employee(db, code="EMP-R", first="Rajatha", last="P", designation="Software Developer",
                         department="IT", email="rajatha18@outlook.com", with_login=False)


def test_rajatha_gets_rajathas_signature_once(client, template, rajatha):
    [res] = run(client, {"email": "rajatha18@outlook.com", "name": "Rajatha"})
    assert "Rajatha P" in res["signature"] and "Software Developer" in res["signature"]
    assert res["signature"].count("Rajatha P") == 1  # appears once
    assert res["disabledClientSignature"] is False  # Outlook is never forced to "No signature"
    report = res["reports"][0]
    assert report["status"] == "inserted" and report["display_name"] == "Rajatha"


def test_signature_replaces_outlooks_own_so_it_appears_once(client, template, rajatha):
    [res] = run(client, {"email": "rajatha18@outlook.com", "name": "Rajatha"}, outlook_default=True)
    assert "OUTLOOK OWN SIGNATURE" not in res["signature"] and "Rajatha P" in res["signature"]
    assert res["disabledClientSignature"] is False


def test_different_employees_get_their_own_signature(client, template, rajatha, john):
    [r] = run(client, {"email": "rajatha18@outlook.com", "name": "Rajatha"})
    [j] = run(client, {"email": "john@company.com", "name": "John Smith"})
    assert "Rajatha P" in r["signature"] and "John Smith" not in r["signature"]
    assert "John Smith" in j["signature"] and "Rajatha" not in j["signature"]


def test_updating_the_employee_updates_the_next_email(client, db, admin_headers, template, rajatha):
    user = {"email": "rajatha18@outlook.com", "name": "Rajatha"}
    [before] = run(client, user)
    assert "Software Developer" in before["signature"]

    emp = db.get(Employee, rajatha.id)
    payload = {"employee_code": emp.employee_code, "first_name": "Rajatha", "last_name": "P",
               "designation": "Senior Software Developer", "department": "IT", "email": emp.email}
    assert client.put(f"/api/employees/{emp.id}", json=payload, headers=admin_headers).status_code == 200
    banner = create_banner(client, admin_headers, "Launch")
    publish(client, admin_headers, banner["id"])

    [after] = run(client, user)
    assert "Senior Software Developer" in after["signature"]
    assert "/banner/current.png" in after["signature"]  # live banner address: always the current banner


def test_reconnecting_and_repeated_emails_never_duplicate(client, admin_headers, template, rajatha):
    results = run(client, {"email": "rajatha18@outlook.com", "name": "Rajatha"}, composes=["auto", "auto", "button", "auto"])
    for res in results:  # each compose window has exactly one Casterly signature
        assert res["signature"].count("Rajatha P") == 1
    status = client.get(f"/api/signatures/{rajatha.id}/outlook-status", headers=admin_headers).json()["data"]
    assert status["addin"] is None  # the harness doesn't hit the server's report endpoint; see lifecycle tests


def test_keep_mode_respects_the_users_own_default(client, admin_headers, template, rajatha):
    client.put("/api/settings", json={**SETTINGS, "addin_replace_outlook_signature": False}, headers=admin_headers)
    [auto] = run(client, {"email": "rajatha18@outlook.com", "name": "Rajatha"}, outlook_default=True)
    assert auto["signature"] == "<p>OUTLOOK OWN SIGNATURE</p>"
    assert auto["reports"][0]["status"] == "kept_outlook_default"
    [button] = run(client, {"email": "rajatha18@outlook.com", "name": "Rajatha"}, composes=["button"], outlook_default=True)
    assert "Rajatha P" in button["signature"]  # the button always inserts it
    assert button["notifications"] == ["Casterly signature added for Rajatha."]


def test_unknown_outlook_user_gets_no_signature_and_an_error_report(client, template):
    [res] = run(client, {"email": "stranger@else.com", "name": "Stranger"})
    assert res["signature"] is None and res["disabledClientSignature"] is False
    assert res["reports"][0]["status"] == "error" and "404" in res["reports"][0]["detail"]


def test_a_default_the_user_chose_stays_selected_across_emails(client, template, rajatha):
    """Once 'Casterly signature' is chosen as the default in Outlook, the add-in never switches it off."""
    results = run(client, {"email": "rajatha18@outlook.com", "name": "Rajatha"},
                  composes=["auto", "auto", "button", "auto", "auto"], outlook_default=True)
    assert all(r["disabledClientSignature"] is False for r in results)
    assert all(r["signature"].count("Rajatha P") == 1 for r in results)


def test_setup_page_uses_the_casterly_signature_name_for_both_defaults(client, template, rajatha):
    from app.api import setup

    page = client.get(f"/setup/{setup.setup_key(rajatha.id)}").text
    assert "name it <b>Casterly signature</b>" in page
    assert "Default for new messages" in page and "Default for replies and forwards" in page
    assert "never" in page and "(no signature)" not in page
