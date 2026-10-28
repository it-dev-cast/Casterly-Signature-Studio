"""Casterly Outlook add-in (new Outlook, Outlook on the web, classic Outlook).

Pasted signatures are a snapshot: Outlook stores its own copy, so banner changes never
reach them. This add-in instead runs on every "new email / reply / forward" and inserts a
freshly generated signature, so the current banner is always used.

    GET /outlook-addin/manifest.xml     the add-in manifest. Employees download it (?download=true)
                                        and add it in Outlook > My Add-ins > Add a custom add-in > Add from File
    GET /outlook-addin/commands.html    runtime page loaded by new Outlook / web
    GET /outlook-addin/launchevent.js   the event handler (also used by classic Outlook)
    GET /api/outlook/signature?email=   signature HTML for the signed-in Outlook user

All of these are public: Outlook loads them without any Signature Studio login. The
signature endpoint only returns what is sent in every email anyway, for ACTIVE employees.
Outlook requires every URL in the manifest to be public HTTPS; all of them are built from
PUBLIC_BASE_URL, so the manifest, runtime files, icons, signature API and banner always agree.

Classic Outlook for Windows does not use this add-in for its saved signature: employees run
the per-employee installer instead (app/installer.py).
"""
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.database.database import get_db
from app.core.dependencies import require_admin
from app.database.models import AuditAction, AuditLog, Employee, OutlookAddinStatus, User
from app.database.types import utcnow
from app.services import employee_service, settings_service, signature_service
from app.utils.urls import is_temporary_tunnel, outlook_url_problem

logger = logging.getLogger("signature_studio.outlook")

ADDIN_ID = "3c2fd8a4-20c3-4340-98ad-515e118a4626"  # fixed, so re-adding replaces the old copy
ADDIN_VERSION_BASE = "1.1"


def addin_version(base: str) -> str:
    """Version changes whenever the manifest changes: its server address or its content.

    Outlook caches add-in manifests by id + version; if the address changes (e.g. a new
    public URL) but the version doesn't, Outlook keeps loading files from the old address.
    The same goes for a changed button or event, so the whole manifest is hashed.
    """
    import zlib

    return f"{ADDIN_VERSION_BASE}.{zlib.crc32(_manifest_template(base).encode()) % 60000}.0"

router = APIRouter(tags=["outlook add-in"])
admin_router = APIRouter(tags=["outlook add-in"])
NO_CACHE = {"Cache-Control": "no-cache, max-age=0"}


def _base() -> str:
    return get_settings().public_base_url


def warn_if_unusable_public_url() -> None:
    """Logged at startup: an add-in manifest built from a bad PUBLIC_BASE_URL won't install."""
    base = _base()
    problem = outlook_url_problem(base)
    if problem:
        logger.warning("PUBLIC_BASE_URL=%s cannot be used by the Outlook add-in: %s. Setup links, the classic "
                       "Outlook installer and signature downloads still work; the add-in needs the public "
                       "https:// address of this server.", base, problem)
    elif is_temporary_tunnel(base):
        logger.warning("PUBLIC_BASE_URL=%s is a Cloudflare quick tunnel: it changes whenever the tunnel restarts, "
                       "and setup links, installed add-ins and installers made with an older address stop "
                       "working. Re-send setup links after every restart.", base)


# ------------------------------------------------------------------ signature --
MODE_HEADER = "X-Casterly-Signature-Mode"  # "keep" | "replace" (see AppSettings.addin_replace_outlook_signature)


def _find_employee(db: Session, email: str) -> Employee | None:
    return db.scalar(select(Employee).where(func.lower(Employee.email) == email.strip().lower()))


@router.get("/api/outlook/signature", response_class=HTMLResponse)
def outlook_signature(email: str = Query(..., min_length=3, max_length=255), db: Session = Depends(get_db)):
    employee = _find_employee(db, email)
    if employee is None or not employee.is_active:
        raise AppError(404, "EMPLOYEE_NOT_FOUND", "No active Signature Studio employee uses this email address.")
    # Called on every new email, so it is deliberately not written to the audit log.
    # versioned_banner: the banner URL changes with each new or edited banner, so Outlook's image
    # cache can't keep showing the old one.
    result = signature_service.generate_employee_signature(db, employee.id, live_banner=True,
                                                           versioned_banner=True)
    mode = "replace" if settings_service.get_app_settings(db).addin_replace_outlook_signature else "keep"
    return HTMLResponse(result.html, headers={"Cache-Control": "no-store", MODE_HEADER: mode})


REPORT_STATUSES = {"inserted", "kept_outlook_default", "error"}


@router.get("/api/outlook/report", status_code=204)
def outlook_report(
    email: str = Query("", max_length=255),
    source: str = Query("", max_length=20),
    status: str = Query("", max_length=30),
    detail: str = Query("", max_length=500),
    host: str = Query("", max_length=100),
    outlook_default: str = Query("", max_length=10),  # "true" | "false" | "" (unknown)
    display_name: str = Query("", max_length=200),  # Office.js userProfile.displayName
    db: Session = Depends(get_db),
):
    """What the add-in did in this Outlook. Stored per employee (one row, updated in place)."""
    logger.info(
        "Outlook add-in report: email=%s name=%s source=%s status=%s outlook_default=%s host=%s detail=%s",
        email, display_name, source, status, outlook_default, host, detail,
    )
    employee = _find_employee(db, email) if email else None
    if employee is None or status not in REPORT_STATUSES:
        return Response(status_code=204)
    now = utcnow()
    row = db.get(OutlookAddinStatus, employee.id)
    if row is None:
        row = OutlookAddinStatus(employee_id=employee.id, last_seen_at=now, last_source="", last_status="")
        db.add(row)
    row.last_seen_at = now
    row.last_source = source[:20] or "auto"
    row.last_status = status
    row.last_detail = detail or None
    row.host = host or None
    row.outlook_display_name = display_name or None
    row.outlook_default_enabled = {"true": True, "false": False}.get(outlook_default)
    if status == "inserted":
        row.last_inserted_at = now
    db.commit()
    return Response(status_code=204)


# ------------------------------------------------------------------ add-in files --
def manifest_xml(base: str) -> str:
    return _manifest_template(base).replace(VERSION_PLACEHOLDER, addin_version(base))


VERSION_PLACEHOLDER = "__VERSION__"


def _manifest_template(base: str) -> str:
    icon = f"{base}/static/brand/icon"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<OfficeApp xmlns="http://schemas.microsoft.com/office/appforoffice/1.1"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xmlns:bt="http://schemas.microsoft.com/office/officeappbasictypes/1.0"
           xmlns:mailappor="http://schemas.microsoft.com/office/mailappversionoverrides/1.0"
           xsi:type="MailApp">
  <Id>{ADDIN_ID}</Id>
  <Version>{VERSION_PLACEHOLDER}</Version>
  <ProviderName>Casterly Private Limited</ProviderName>
  <DefaultLocale>en-US</DefaultLocale>
  <DisplayName DefaultValue="Casterly Signatures"/>
  <Description DefaultValue="Adds your up-to-date Casterly email signature to new emails, replies and forwards."/>
  <IconUrl DefaultValue="{icon}-64.png"/>
  <HighResolutionIconUrl DefaultValue="{icon}-128.png"/>
  <SupportUrl DefaultValue="{base}/outlook-addin/commands.html"/>
  <AppDomains>
    <AppDomain>{base}</AppDomain>
  </AppDomains>
  <Hosts>
    <Host Name="Mailbox"/>
  </Hosts>
  <Requirements>
    <Sets>
      <Set Name="Mailbox" MinVersion="1.1"/>
    </Sets>
  </Requirements>
  <FormSettings>
    <Form xsi:type="ItemRead">
      <DesktopSettings>
        <SourceLocation DefaultValue="{base}/outlook-addin/commands.html"/>
        <RequestedHeight>250</RequestedHeight>
      </DesktopSettings>
    </Form>
  </FormSettings>
  <Permissions>ReadWriteItem</Permissions>
  <Rule xsi:type="RuleCollection" Mode="Or">
    <Rule xsi:type="ItemIs" ItemType="Message" FormType="Read"/>
  </Rule>
  <DisableEntityHighlighting>false</DisableEntityHighlighting>
  <VersionOverrides xmlns="http://schemas.microsoft.com/office/mailappversionoverrides" xsi:type="VersionOverridesV1_0">
    <VersionOverrides xmlns="http://schemas.microsoft.com/office/mailappversionoverrides/1.1" xsi:type="VersionOverridesV1_1">
      <Requirements>
        <bt:Sets DefaultMinVersion="1.10">
          <bt:Set Name="Mailbox"/>
        </bt:Sets>
      </Requirements>
      <Hosts>
        <Host xsi:type="MailHost">
          <Runtimes>
            <!-- new Outlook / web use the HTML page; classic Outlook on Windows uses the JS file -->
            <Runtime resid="WebViewRuntime.Url">
              <Override type="javascript" resid="JSRuntime.Url"/>
            </Runtime>
          </Runtimes>
          <DesktopFormFactor>
            <FunctionFile resid="WebViewRuntime.Url"/>
            <ExtensionPoint xsi:type="LaunchEvent">
              <LaunchEvents>
                <LaunchEvent Type="OnNewMessageCompose" FunctionName="onNewMessageComposeHandler"/>
              </LaunchEvents>
              <SourceLocation resid="WebViewRuntime.Url"/>
            </ExtensionPoint>
            <!-- Manual fallback: a button in the compose window (works on every account type) -->
            <ExtensionPoint xsi:type="MessageComposeCommandSurface">
              <OfficeTab id="TabDefault">
                <Group id="casterlyComposeGroup">
                  <Label resid="Group.Label"/>
                  <Control xsi:type="Button" id="casterlyInsertSignature">
                    <Label resid="Insert.Label"/>
                    <Supertip>
                      <Title resid="Insert.Label"/>
                      <Description resid="Insert.Tooltip"/>
                    </Supertip>
                    <Icon>
                      <bt:Image size="16" resid="Icon.16x16"/>
                      <bt:Image size="32" resid="Icon.32x32"/>
                      <bt:Image size="80" resid="Icon.80x80"/>
                    </Icon>
                    <Action xsi:type="ExecuteFunction">
                      <FunctionName>insertCasterlySignature</FunctionName>
                    </Action>
                  </Control>
                </Group>
              </OfficeTab>
            </ExtensionPoint>
          </DesktopFormFactor>
        </Host>
      </Hosts>
      <Resources>
        <bt:Images>
          <bt:Image id="Icon.16x16" DefaultValue="{icon}-16.png"/>
          <bt:Image id="Icon.32x32" DefaultValue="{icon}-32.png"/>
          <bt:Image id="Icon.80x80" DefaultValue="{icon}-80.png"/>
        </bt:Images>
        <bt:Urls>
          <bt:Url id="WebViewRuntime.Url" DefaultValue="{base}/outlook-addin/commands.html"/>
          <bt:Url id="JSRuntime.Url" DefaultValue="{base}/outlook-addin/launchevent.js"/>
        </bt:Urls>
        <bt:ShortStrings>
          <bt:String id="Group.Label" DefaultValue="Casterly"/>
          <bt:String id="Insert.Label" DefaultValue="Insert Casterly signature"/>
        </bt:ShortStrings>
        <bt:LongStrings>
          <bt:String id="Insert.Tooltip" DefaultValue="Adds your up-to-date Casterly signature with the current banner."/>
        </bt:LongStrings>
      </Resources>
    </VersionOverrides>
  </VersionOverrides>
</OfficeApp>
"""


LAUNCH_EVENT_JS = """// Casterly Signatures - adds the up-to-date signature to emails.
// Runs automatically when a new email / reply / forward opens, and from the
// "Insert Casterly signature" button in the compose window.
//
// It NEVER changes the user's Outlook signature settings: it does not call
// disableClientSignatureAsync (which switches Outlook's default to "no signature").
// setSignatureAsync replaces any signature already in the email, so there is no duplicate.
var SIGNATURE_API = "__BASE__/api/outlook/signature";
var REPORT_API = "__BASE__/api/outlook/report";

// The signed-in Outlook user: their email picks the employee (Microsoft user -> employee ->
// signature); their display name (e.g. "Rajatha") is shown in messages and reported.
function currentUser() {
  var profile = Office.context.mailbox.userProfile;
  return { email: profile.emailAddress, name: profile.displayName || profile.emailAddress };
}

function describe(error) {
  if (!error) return "";
  return String((error.name ? error.name + ": " : "") + (error.message || error)).substring(0, 400);
}

function report(source, status, outlookDefault, error, then) {
  var host = "";
  try { host = Office.context.diagnostics.platform + " " + Office.context.diagnostics.version; } catch (e) {}
  var user = currentUser();
  var params = "email=" + encodeURIComponent(user.email) + "&display_name=" + encodeURIComponent(user.name) +
    "&source=" + source + "&status=" + status + "&host=" + encodeURIComponent(host) +
    "&outlook_default=" + (outlookDefault === null ? "" : String(outlookDefault)) +
    "&detail=" + encodeURIComponent(describe(error));
  var finished = false;
  var finish = function () { if (!finished) { finished = true; then(); } };
  setTimeout(finish, 3000);  // never hold Outlook up for the report
  fetch(REPORT_API + "?" + params, { cache: "no-store" }).then(finish, finish);
}

// Is the user's own Outlook default signature switched on? true / false / null (unknown).
function outlookDefaultEnabled(callback) {
  var item = Office.context.mailbox.item;
  if (!item.isClientSignatureEnabledAsync) return callback(null);
  item.isClientSignatureEnabledAsync(function (r) {
    callback(r.status === "succeeded" ? r.value === true : null);
  });
}

// Always fetched fresh (no cache), so the latest details, banner and logo are used.
function fetchSignature() {
  var email = currentUser().email;
  return fetch(SIGNATURE_API + "?email=" + encodeURIComponent(email), { cache: "no-store" }).then(function (response) {
    if (!response.ok) throw new Error("No Casterly signature for " + email + " (HTTP " + response.status + ")");
    var mode = response.headers.get("X-Casterly-Signature-Mode") || "replace";
    return response.text().then(function (html) { return { html: html, mode: mode }; });
  });
}

function putSignature(html, done) {
  var body = Office.context.mailbox.item.body;
  var after = function (r) { done(r.status === "succeeded" ? null : r.error); };
  if (body.setSignatureAsync) {
    // Replaces a signature already in this email (e.g. Outlook's own) - no duplicates.
    body.setSignatureAsync(html, { coercionType: Office.CoercionType.Html }, after);
  } else {
    body.setSelectedDataAsync(html, { coercionType: Office.CoercionType.Html }, after);  // older clients
  }
}

function notify(message) {
  try {
    Office.context.mailbox.item.notificationMessages.replaceAsync("casterly", {
      type: Office.MailboxEnums.ItemNotificationMessageType.InformationalMessage,
      message: message.substring(0, 150), icon: "Icon.16x16", persistent: false
    });
  } catch (e) { /* notifications are best-effort */ }
}

// Automatic: new email, reply or forward.
function onNewMessageComposeHandler(event) {
  outlookDefaultEnabled(function (outlookDefault) {
    fetchSignature().then(function (sig) {
      if (outlookDefault === true && sig.mode !== "replace") {
        // The user chose their own default signature in Outlook: respect it.
        report("auto", "kept_outlook_default", outlookDefault, null, function () { event.completed(); });
        return;
      }
      putSignature(sig.html, function (error) {
        if (error) console.log("Casterly Signatures: " + describe(error));
        report("auto", error ? "error" : "inserted", outlookDefault, error, function () { event.completed(); });
      });
    }).catch(function (error) {
      console.log("Casterly Signatures: " + describe(error));
      report("auto", "error", outlookDefault, error, function () { event.completed(); });
    });
  });
}

// Manual: the compose-window button - always inserts the Casterly signature.
function insertCasterlySignature(event) {
  outlookDefaultEnabled(function (outlookDefault) {
    fetchSignature().then(function (sig) {
      putSignature(sig.html, function (error) {
        notify(error ? "Casterly signature could not be added: " + describe(error) : "Casterly signature added for " + currentUser().name + ".");
        report("button", error ? "error" : "inserted", outlookDefault, error, function () { event.completed(); });
      });
    }).catch(function (error) {
      notify("Casterly signature could not be added: " + describe(error));
      report("button", "error", outlookDefault, error, function () { event.completed(); });
    });
  });
}

Office.onReady(function () {});
Office.actions.associate("onNewMessageComposeHandler", onNewMessageComposeHandler);
Office.actions.associate("insertCasterlySignature", insertCasterlySignature);
"""

COMMANDS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="X-UA-Compatible" content="IE=Edge" />
  <title>Casterly Signatures</title>
  <script src="https://appsforoffice.microsoft.com/lib/1/hosted/office.js"></script>
  <script src="__BASE__/outlook-addin/launchevent.js"></script>
</head>
<body style="font-family:Segoe UI,Arial,sans-serif;color:#374151;padding:16px">
  <p><strong>Casterly Signatures</strong> adds your email signature automatically when you write an email.</p>
</body>
</html>
"""


@router.get("/outlook-addin/manifest.xml")
def manifest(download: bool = False):
    headers = dict(NO_CACHE)
    if download:
        headers["Content-Disposition"] = 'attachment; filename="casterly-signatures-manifest.xml"'
    return Response(manifest_xml(_base()), media_type="application/xml", headers=headers)


@router.get("/outlook-addin/launchevent.js")
def launch_event_js():
    return Response(LAUNCH_EVENT_JS.replace("__BASE__", _base()), media_type="application/javascript", headers=NO_CACHE)


@router.get("/outlook-addin/commands.html", response_class=HTMLResponse)
def commands_html():
    return HTMLResponse(COMMANDS_HTML.replace("__BASE__", _base()), headers=NO_CACHE)


# ------------------------------------------------------------------ status (admin) --
@admin_router.get("/signatures/{employee_id}/outlook-status")
def outlook_status(employee_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """What we actually know about this employee's Outlook - nothing is guessed."""
    employee = employee_service.get_employee(db, employee_id)
    row = db.get(OutlookAddinStatus, employee.id)
    classic = db.scalar(
        select(AuditLog.created_at)
        .where(AuditLog.action == AuditAction.SIGNATURE_INSTALLED.value, AuditLog.entity_id == str(employee.id))
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    return {"success": True, "data": {
        "addin": None if row is None else {
            "last_seen_at": row.last_seen_at,
            "last_source": row.last_source,
            "last_status": row.last_status,
            "last_detail": row.last_detail,
            "host": row.host,
            "outlook_display_name": row.outlook_display_name,
            "outlook_email": employee.email,
            "outlook_default_enabled": row.outlook_default_enabled,
            "last_inserted_at": row.last_inserted_at,
        },
        "classic_installed_at": classic,
        "replace_outlook_signature": settings_service.get_app_settings(db).addin_replace_outlook_signature,
        # Office.js has no API to create saved signatures or change Outlook's default signature.
        "addin_can_set_default": False,
    }}
