"""Outlook signature lifecycle: the add-in never forces "No signature", reports what it did,
never duplicates, and the admin can see the real state (including what is NOT supported)."""
from sqlalchemy import func, select

from app.database.models import OutlookAddinStatus

SETTINGS = {"company_name": "Casterly Private Limited", "company_website": None, "legal_disclaimer": None}


def _report(client, email="john@company.com", **params):
    q = {"email": email, "source": "auto", "status": "inserted", "outlook_default": "false", "host": "OfficeOnline"}
    q.update(params)
    return client.get("/api/outlook/report", params=q)


# ------------------------------------------------------ the root cause --
def test_addin_never_disables_the_users_outlook_signature(client):
    js = client.get("/outlook-addin/launchevent.js").text
    # disableClientSignatureAsync switches Outlook's default to "no signature" (Microsoft docs).
    assert "disableClientSignatureAsync(" not in js
    # It checks the user's own setting instead, and respects it unless the admin chose "replace".
    assert "isClientSignatureEnabledAsync" in js
    assert 'outlookDefault === true && sig.mode !== "replace"' in js
    assert "kept_outlook_default" in js


def test_no_page_tells_users_to_choose_no_signature(client, template, john):
    from app.api import setup

    page = client.get(f"/setup/{setup.setup_key(john.id)}").text.lower()
    assert "(no signature)" not in page
    assert "existing outlook signatures are not changed" in page


def test_signature_endpoint_tells_the_addin_the_mode(client, admin_headers, template, john):
    r = client.get("/api/outlook/signature?email=john@company.com")
    assert r.headers["x-casterly-signature-mode"] == "replace"  # default: the Signature Studio signature is used
    client.put("/api/settings", json={**SETTINGS, "addin_replace_outlook_signature": False}, headers=admin_headers)
    r = client.get("/api/outlook/signature?email=john@company.com")
    assert r.headers["x-casterly-signature-mode"] == "keep"


# ---------------------------------------------- status: create & update --
def test_first_report_creates_status_and_reconnecting_updates_it(client, db, admin_headers, template, john):
    assert client.get(f"/api/signatures/{john.id}/outlook-status", headers=admin_headers).json()["data"]["addin"] is None

    assert _report(client).status_code == 204  # first connection
    for _ in range(3):  # reconnecting / composing again with the same account
        _report(client, status="inserted")
    _report(client, display_name="John Smith")
    rows = db.scalar(select(func.count()).select_from(OutlookAddinStatus).where(OutlookAddinStatus.employee_id == john.id))
    assert rows == 1  # one row per employee, updated in place - never duplicated

    data = client.get(f"/api/signatures/{john.id}/outlook-status", headers=admin_headers).json()["data"]
    assert data["addin"]["last_status"] == "inserted" and data["addin"]["last_inserted_at"]
    assert data["addin"]["outlook_default_enabled"] is False
    assert data["addin"]["outlook_display_name"] == "John Smith" and data["addin"]["outlook_email"] == "john@company.com"
    assert data["addin_can_set_default"] is False  # honest: Office.js cannot set Outlook's default


def test_kept_outlook_default_is_recorded_without_losing_last_insert(client, admin_headers, template, john):
    _report(client, status="inserted")
    first = client.get(f"/api/signatures/{john.id}/outlook-status", headers=admin_headers).json()["data"]["addin"]
    _report(client, status="kept_outlook_default", outlook_default="true")
    data = client.get(f"/api/signatures/{john.id}/outlook-status", headers=admin_headers).json()["data"]["addin"]
    assert data["last_status"] == "kept_outlook_default" and data["outlook_default_enabled"] is True
    assert data["last_inserted_at"] == first["last_inserted_at"]


def test_errors_from_outlook_are_reported_not_hidden(client, admin_headers, template, john):
    _report(client, status="error", detail="InvalidFormatError: body is plain text")
    data = client.get(f"/api/signatures/{john.id}/outlook-status", headers=admin_headers).json()["data"]["addin"]
    assert data["last_status"] == "error" and "InvalidFormatError" in data["last_detail"]


def test_reports_for_unknown_emails_or_bad_status_are_ignored(client, db, template, john):
    assert _report(client, email="stranger@else.com").status_code == 204
    assert _report(client, status="whatever").status_code == 204
    assert db.scalar(select(func.count()).select_from(OutlookAddinStatus)) == 0


def test_status_is_admin_only(client, john_headers, john):
    assert client.get(f"/api/signatures/{john.id}/outlook-status", headers=john_headers).status_code == 403


def test_status_shows_classic_installer_runs(client, admin_headers, template, john):
    from app import installer

    client.get(f"/api/installer/signature?e={john.id}&s={installer.employee_key_signature(john.id)}")
    data = client.get(f"/api/signatures/{john.id}/outlook-status", headers=admin_headers).json()["data"]
    assert data["classic_installed_at"]


# ------------------------------------------------------------- settings --
def test_replace_setting_defaults_on_round_trips_and_is_audited(client, admin_headers):
    assert client.get("/api/settings", headers=admin_headers).json()["data"]["addin_replace_outlook_signature"] is True
    r = client.put("/api/settings", json={**SETTINGS, "addin_replace_outlook_signature": False}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["data"]["addin_replace_outlook_signature"] is False
    items = client.get("/api/audit-logs?action=SETTINGS_UPDATED", headers=admin_headers).json()["data"]["items"]
    assert "keeps employees' own default signatures" in items[0]["description"]
    assert client.get("/api/settings", headers=admin_headers).json()["data"]["addin_replace_outlook_signature"] is False


def test_setup_page_describes_replace_mode_accurately(client, admin_headers, template, john):
    from app.api import setup

    client.put("/api/settings", json={**SETTINGS, "addin_replace_outlook_signature": True}, headers=admin_headers)
    page = client.get(f"/setup/{setup.setup_key(john.id)}").text
    assert "takes the place of any other signature" in page and "(no signature)" not in page


def test_status_row_removed_with_employee(client, db, admin_headers, template, john):
    john_id = john.id
    _report(client)
    assert client.delete(f"/api/employees/{john_id}", headers=admin_headers).status_code == 200
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(OutlookAddinStatus).where(OutlookAddinStatus.employee_id == john_id)) == 0
