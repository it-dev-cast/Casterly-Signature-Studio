"""Signature setup emails and the personal "Install your signature" page.

Admin clicks "Send email"  ->  the employee receives their signature + a personal link:
    {PUBLIC_BASE_URL}/setup/<employee-id>.<key>
The link opens a page (no login) with the one-click options that exist for each Outlook:
  - new Outlook / Outlook on the web: download the add-in manifest and add it with
    My Add-ins > Add a custom add-in > Add from File (then fully automatic)
  - classic Outlook on Windows: download the installer (sets new + reply signatures)
  - anything else: copy the signature or download it as an HTML file
A web page cannot change Outlook settings by itself; these are the closest possible steps.
"""
import hashlib
import hmac
import html
import base64

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import installer
from app.core.config import get_settings
from app.core.dependencies import require_admin
from app.core.errors import AppError
from app.database.database import get_db
from app.database.models import AuditAction, Employee, User
from app.renderers.html_utils import html_to_text
from app.schemas.common import ApiResponse, ok
from app.services import audit_service, email_service, employee_service, settings_service, signature_service
from app.utils.urls import outlook_url_problem

admin_router = APIRouter(tags=["signature setup"])
public_router = APIRouter(tags=["signature setup"])


# ---------------------------------------------------------------- keys --
def setup_key(employee_id: int) -> str:
    mac = hmac.new(get_settings().secret_key.encode(), f"sig-setup:{employee_id}".encode(), hashlib.sha256)
    return f"{employee_id}.{base64.urlsafe_b64encode(mac.digest()[:18]).decode().rstrip('=')}"


def setup_link(employee_id: int) -> str:
    return f"{get_settings().public_base_url}/setup/{setup_key(employee_id)}"


def _employee_for_key(db: Session, key: str) -> Employee:
    eid_text, _, _sig = key.partition(".")
    if not eid_text.isdigit() or not hmac.compare_digest(setup_key(int(eid_text)), key):
        raise AppError(404, "INVALID_SETUP_LINK", "This setup link is not valid. Ask your administrator to send a new one.")
    employee = db.get(Employee, int(eid_text))
    if employee is None or not employee.is_active:
        raise AppError(404, "INVALID_SETUP_LINK", "This setup link is no longer active.")
    return employee


# --------------------------------------------------------------- email --
def _email_html(employee: Employee, company: str, signature_html: str, link: str) -> str:
    e = html.escape
    return f"""<!DOCTYPE html><html><body style="margin:0;padding:24px;background:#f5f5fa;font-family:Arial,Helvetica,sans-serif;color:#374151;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="640" style="max-width:640px;width:100%;margin:0 auto;background:#ffffff;border-radius:12px;border-collapse:separate;">
<tr><td style="height:4px;background:#678b27;border-radius:12px 12px 0 0;font-size:0;line-height:0;">&nbsp;</td></tr>
<tr><td style="padding:28px 32px 8px 32px;">
  <p style="margin:0 0 12px 0;font-size:18px;font-weight:bold;color:#1f2937;">Hi {e(employee.first_name)}, your email signature is ready</p>
  <p style="margin:0 0 20px 0;font-size:14px;line-height:21px;">{e(company)} has created your official email signature. Click the button below to add it to Outlook. It will then be added automatically to your new emails and replies.</p>
  <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td style="background:#678b27;border-radius:8px;">
    <a href="{e(link)}" target="_blank" style="display:inline-block;padding:12px 24px;font-size:15px;font-weight:bold;color:#ffffff;text-decoration:none;">Set up my signature</a>
  </td></tr></table>
  <p style="margin:16px 0 0 0;font-size:12px;color:#6b7280;">Or open this link: <a href="{e(link)}" style="color:#678b27;">{e(link)}</a></p>
</td></tr>
<tr><td style="padding:24px 32px 8px 32px;"><p style="margin:0;font-size:12px;font-weight:bold;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">Your signature</p></td></tr>
<tr><td style="padding:8px 32px 32px 32px;"><div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;">{signature_html}</div></td></tr>
</table></body></html>"""


def _email_body(employee: Employee, company: str, signature_html: str, link: str) -> str:
    full = _email_html(employee, company, signature_html, link)
    start = full.index("<table"); end = full.rindex("</body>")
    return full[start:end]


def _email_text(employee: Employee, company: str, signature_html: str, link: str) -> str:
    return (
        f"Hi {employee.first_name},\n\n{company} has created your official email signature.\n"
        f"Open this link to add it to Outlook:\n{link}\n\nYour signature:\n\n{html_to_text(signature_html)}\n"
    )


class SetupLinkRead(BaseModel):
    employee_id: int
    email: str
    link: str
    subject: str
    email_configured: bool
    email_html: str = ""  # ready-made message body (clickable button + signature), for pasting


class SetupEmailRead(SetupLinkRead):
    sent: bool


def _subject(company: str) -> str:
    return f"Your {company} email signature is ready"


@admin_router.get("/signatures/{employee_id}/setup-link", response_model=ApiResponse[SetupLinkRead])
def get_setup_link(employee_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    employee = employee_service.get_employee(db, employee_id)
    company = settings_service.get_app_settings(db).company_name
    link = setup_link(employee.id)
    signature = signature_service.generate_employee_signature(db, employee.id).live_html
    return ok({
        "employee_id": employee.id, "email": employee.email, "link": link,
        "subject": _subject(company), "email_configured": email_service.is_configured(),
        "email_html": _email_body(employee, company, signature, link),
    })


@admin_router.post("/signatures/{employee_id}/send-setup-email", response_model=ApiResponse[SetupEmailRead])
def send_setup_email(employee_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    employee = employee_service.get_employee(db, employee_id)
    if not employee.is_active:
        raise AppError(409, "EMPLOYEE_INACTIVE", "Activate this employee before sending their signature.")
    company = settings_service.get_app_settings(db).company_name
    signature = signature_service.generate_employee_signature(db, employee.id).live_html
    link = setup_link(employee.id)
    email_service.send_email(
        employee.email, _subject(company),
        _email_html(employee, company, signature, link), _email_text(employee, company, signature, link),
    )
    audit_service.record(
        db, AuditAction.SIGNATURE_SETUP_EMAIL_SENT, user_id=admin.id, entity_type="employee",
        entity_id=employee.id, description=f"Sent the signature setup email to {employee.full_name} ({employee.email})",
    )
    db.commit()
    return ok({
        "employee_id": employee.id, "email": employee.email, "link": link, "subject": _subject(company),
        "email_configured": True, "sent": True,
    })


# --------------------------------------------------------- setup page --
@public_router.get("/setup/{key}/installer")
def setup_installer(key: str, db: Session = Depends(get_db)):
    employee = _employee_for_key(db, key)
    if not installer.INSTALLER_FILE.is_file():
        raise AppError(503, "INSTALLER_UNAVAILABLE", "The installer is not available on this server.")
    return FileResponse(
        installer.INSTALLER_FILE, media_type="application/vnd.microsoft.portable-executable",
        filename=installer.installer_filename(employee.id), headers={"Cache-Control": "no-store"},
    )


@public_router.get("/setup/{key}/signature.html")
def setup_signature_html(key: str, db: Session = Depends(get_db)):
    """The signature as a standalone HTML file, for email apps other than Outlook."""
    employee = _employee_for_key(db, key)
    signature = signature_service.generate_employee_signature(db, employee.id).live_html
    filename = f"{employee.employee_code}-signature.html"
    return Response(
        signature_service.wrap_document(signature, f"{employee.full_name} - Signature"),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


@public_router.get("/setup/{key}", response_class=HTMLResponse)
def setup_page(key: str, db: Session = Depends(get_db)):
    try:
        employee = _employee_for_key(db, key)
    except AppError as err:
        return HTMLResponse(_page("Link not valid", f"<p>{html.escape(err.message)}</p>"), status_code=404)
    base = get_settings().public_base_url
    app_settings = settings_service.get_app_settings(db)
    company = app_settings.company_name
    signature = signature_service.generate_employee_signature(db, employee.id).live_html
    manifest = f"{base}/outlook-addin/manifest.xml"
    e = html.escape
    if outlook_url_problem(base):
        # Outlook can't load add-in files from this server address; don't offer a manifest that won't install.
        addin_steps = ("<p><b>The Outlook add-in isn't available yet.</b> Please ask your administrator, "
                       "or use the other options below for now.</p>")
    else:
        addin_steps = f"""<ol>
    <li><a class="btn" href="{e(manifest)}?download=true">Download Outlook Add-in Manifest</a></li>
    <li>Open Outlook and go to <b>My Add-ins</b> (in Outlook on the web you can also open
      <a href="https://aka.ms/olksideload" target="_blank" rel="noopener">aka.ms/olksideload</a>; sign in with <b>{e(employee.email)}</b> if asked).</li>
    <li>Choose <b>Add a custom add-in</b>.</li>
    <li>Choose <b>Add from File</b>.</li>
    <li>Select the downloaded <b>casterly-signatures-manifest.xml</b> file.</li>
    <li>Click <b>Install</b>.</li>
    <li>Create a new email and check that your Casterly signature is inserted automatically. If it isn't, click
      <b>Insert Casterly signature</b> in the new email's toolbar.</li>
  </ol>
  <p class="small"><b>Optional:</b> to also keep it in Outlook's own signature list (Microsoft doesn't let add-ins do this),
    click <button onclick="copySignature(this)">Copy signature</button>, open <b>Settings → Accounts → Signatures</b>,
    click <b>+ Add signature</b>, name it <b>Casterly signature</b>, paste (Ctrl+V) and <b>Save</b>. You can then choose it for
    <b>Default for new messages</b> and <b>Default for replies and forwards</b>; Signature Studio never switches it back to
    "No signature".</p>"""
    # Describe exactly what the add-in will do - it never changes Outlook's signature settings.
    if app_settings.addin_replace_outlook_signature:
        existing = ("Your existing Outlook signatures are not changed or removed. In each new email the "
                    "Casterly signature takes the place of any other signature, so you won't get two.")
    else:
        existing = ("Your existing Outlook signatures are not changed or removed. If you have chosen a default "
                    "signature in Outlook, it is kept; the Casterly signature is added automatically when no "
                    "default is set. You can always add it with <b>Insert Casterly signature</b> in a new email.")
    body = f"""
<p class="lead">Hi {e(employee.first_name)}, here is your {e(company)} email signature. Choose the Outlook you use below.</p>
<div class="preview">{signature}</div>

<section>
  <h2><span class="n">1</span> New Outlook or Outlook on the web</h2>
  <p>Add the Casterly add-in once. After that your signature is added <b>automatically</b> to every new email, reply and forward, and banner updates appear by themselves.</p>
  {addin_steps}
  <p class="small">{existing}</p>
</section>

<section>
  <h2><span class="n">2</span> Classic Outlook for Windows</h2>
  <p>The installer adds the Casterly signature to classic Outlook and, the first time, makes it your default for new emails, replies and forwards. Running it again updates the same signature and keeps whichever default you have chosen. Don't rename the file.</p>
  <ol>
    <li><a class="btn" href="{e(base)}/setup/{e(key)}/installer">Download Outlook Installer</a></li>
    <li>Run the downloaded <b>.exe</b> file. If Windows says "Windows protected your PC", click <b>More info → Run anyway</b>.</li>
    <li>Restart Outlook.</li>
    <li>Check that <b>Casterly signature</b> appears in <b>File → Options → Mail → Signatures</b>.</li>
  </ol>
</section>

<section>
  <h2><span class="n">3</span> Any other email app</h2>
  <p>Copy your signature and paste it into your email app's signature settings, or download it as an HTML file.</p>
  <div class="row"><button onclick="copySignature(this)">Copy signature</button>
  <a class="btn light" href="{e(base)}/setup/{e(key)}/signature.html">Download Signature HTML</a></div>
</section>
<template id="sig">{signature}</template>
"""
    return HTMLResponse(_page(f"{company} email signature", body), headers={"Cache-Control": "no-store"})


def _page(title: str, body: str) -> str:
    e = html.escape
    logo = f"{get_settings().public_base_url}/static/brand/casterly-logo.png"
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<style>
 body{{margin:0;background:#f6f6fb;font-family:Segoe UI,Arial,sans-serif;color:#374151}}
 .wrap{{max-width:760px;margin:0 auto;padding:32px 16px}}
 .card{{background:#fff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden}}
 .bar{{height:3px;background:linear-gradient(90deg,#678b27,#9cba64,#c3d05b)}}
 .inner{{padding:28px}}
 header{{display:flex;align-items:center;gap:12px;margin-bottom:20px}} header img{{height:44px}}
 h1{{font-size:20px;margin:0;color:#111827}} h2{{font-size:16px;margin:0 0 6px;color:#111827;display:flex;align-items:center;gap:8px}}
 .n{{display:inline-flex;width:22px;height:22px;border-radius:50%;background:#eef4e1;color:#678b27;font-size:12px;align-items:center;justify-content:center}}
 .lead{{margin:0 0 16px}} .preview{{border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin-bottom:8px;overflow-x:auto}}
 section{{border-top:1px solid #f0f0f5;padding-top:20px;margin-top:20px}} p,li{{font-size:14px;line-height:1.55}} .small{{font-size:12px;color:#6b7280}}
 a{{color:#678b27}} .row{{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}}
 input{{flex:1;min-width:240px;padding:9px 10px;border:1px solid #d1d5db;border-radius:8px;font-size:13px}}
 button,.btn{{background:#678b27;color:#fff;border:0;border-radius:8px;padding:9px 16px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block}}
 .btn.light{{background:#fff;color:#678b27;border:1px solid #dbe7c2}}
</style></head><body><div class="wrap"><div class="card"><div class="bar"></div><div class="inner">
<header><img src="{e(logo)}" alt=""><h1>{e(title)}</h1></header>
{body}
</div></div></div>
<script>
function done(b,t){{var o=b.textContent;b.textContent=t;setTimeout(function(){{b.textContent=o}},2000)}}
function copyText(id,b){{var i=document.getElementById(id);i.select();navigator.clipboard.writeText(i.value).then(function(){{done(b,'Copied')}})}}
function copySignature(b){{var h=document.getElementById('sig').innerHTML;
 if(window.ClipboardItem){{navigator.clipboard.write([new ClipboardItem({{'text/html':new Blob([h],{{type:'text/html'}}),'text/plain':new Blob([document.querySelector('.preview').innerText],{{type:'text/plain'}})}})]).then(function(){{done(b,'Copied')}})}}
 else{{navigator.clipboard.writeText(h).then(function(){{done(b,'Copied (HTML)')}})}}}}
</script></body></html>"""
