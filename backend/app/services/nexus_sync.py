"""Keep Signature Studio's employees in sync with nexusAuth.

nexusAuth is the source of truth for employee records. Signature Studio signs in to
nexusAuth's REST API with a service account (NEXUSAUTH_EMAIL / NEXUSAUTH_PASSWORD),
reads every employee (exited ones included) and:

  * creates an employee here for each new nexusAuth employee,
  * updates the synced fields when they changed in nexusAuth,
  * deactivates the employee here when it is exited (or gone) in nexusAuth.

Existing Signature Studio employees are linked by email on the first sync, so nobody is
duplicated. The synced fields (SYNCED_FIELDS) are then owned by nexusAuth and cannot be
edited here; signature-only fields (mobile, website, X, Instagram, other link, display
name) stay editable in Signature Studio.

Photos: a photo uploaded in nexusAuth is copied into Signature Studio's own uploads (nexusAuth
is usually not reachable by email recipients), stored as /uploads/photos/nexus-<hash>.<ext>,
and replaces any photo set here. It is only downloaded again when it changes in nexusAuth.
Removing it in nexusAuth removes the copy; a photo added here is kept while nexusAuth has none.

Only the fields a signature needs are copied. nexusAuth's sensitive data (bank, PAN,
Aadhaar, residence proof) is never read into Signature Studio.

A background thread started by app.main runs the sync every NEXUSAUTH_SYNC_SECONDS;
admins can also run it on demand ("Sync now").
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models import AuditAction, Employee, UserRole
from app.database.types import utcnow
from app.core.errors import AppError
from app.services import audit_service, storage_service
from app.utils import validators as v

logger = logging.getLogger(__name__)

# Fields nexusAuth owns for a linked employee.
SYNCED_FIELDS = (
    "employee_code", "first_name", "last_name", "designation", "department", "company",
    "email", "phone", "linkedin_url", "address", "is_active",
)
PAGE_SIZE = 100
# Photos copied from nexusAuth are stored under this prefix, so they can be told apart from photos
# uploaded in Signature Studio.
NEXUS_PHOTO_PREFIX = "/uploads/photos/nexus-"
# nexusAuth serves uploaded photos from its own /uploads/ folder; only such paths are downloaded.
_NEXUS_UPLOAD_PATH = re.compile(r"^/uploads/[A-Za-z0-9_\-/]+\.[A-Za-z0-9]+$")


class NexusAuthError(Exception):
    """nexusAuth could not be reached, rejected the sign-in or returned something unexpected."""


class NexusAuthLoginRejected(NexusAuthError):
    """Wrong credentials. The background sync stops retrying so nexusAuth doesn't lock the account."""


# ------------------------------------------------------------------ client --
class NexusAuthClient:
    """Minimal nexusAuth API client: sign in, keep the token fresh, read paged lists."""

    def __init__(self, base_url: str, email: str, password: str, transport: httpx.BaseTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self._http = httpx.Client(base_url=self.base_url, timeout=15, transport=transport)
        self._access: str | None = None
        self._refresh: str | None = None
        self._expires_at = 0.0

    def close(self) -> None:
        self._http.close()

    def _store_tokens(self, data: dict) -> None:
        self._access = data["access_token"]
        self._refresh = data.get("refresh_token")
        self._expires_at = time.monotonic() + max(int(data.get("expires_in", 60)) - 30, 10)

    def _login(self) -> None:
        try:
            r = self._http.post("/api/v1/auth/login", json={"email": self.email, "password": self.password})
        except httpx.HTTPError as err:
            raise NexusAuthError(f"Cannot reach nexusAuth at {self.base_url} ({err.__class__.__name__}).") from None
        if r.status_code in (401, 403, 423):
            raise NexusAuthLoginRejected(
                "nexusAuth rejected the sign-in. Check NEXUSAUTH_EMAIL and NEXUSAUTH_PASSWORD "
                "(the account must be an active operator or admin)."
            )
        if r.status_code == 429:
            raise NexusAuthError("nexusAuth is rate-limiting sign-ins. The next sync will try again.")
        if r.status_code != 200:
            raise NexusAuthError(f"nexusAuth sign-in failed (HTTP {r.status_code}).")
        self._store_tokens(r.json()["data"])

    def _refresh_tokens(self) -> bool:
        if not self._refresh:
            return False
        try:
            r = self._http.post("/api/v1/auth/refresh", json={"refresh_token": self._refresh})
        except httpx.HTTPError:
            return False
        if r.status_code != 200:
            return False
        self._store_tokens(r.json()["data"])
        return True

    def _token(self) -> str:
        if self._access is None or time.monotonic() >= self._expires_at:
            if not self._refresh_tokens():
                self._login()
        assert self._access is not None
        return self._access

    def _get(self, path: str, params: dict) -> dict:
        for attempt in (1, 2):
            try:
                r = self._http.get(path, params=params, headers={"Authorization": f"Bearer {self._token()}"})
            except httpx.HTTPError as err:
                raise NexusAuthError(f"Cannot reach nexusAuth at {self.base_url} ({err.__class__.__name__}).") from None
            if r.status_code == 401 and attempt == 1:
                self._access = None  # expired or revoked: sign in again once
                continue
            if r.status_code == 403:
                raise NexusAuthError(
                    "The nexusAuth account has no permission to read employees. Use an operator or admin account."
                )
            if r.status_code != 200:
                raise NexusAuthError(f"nexusAuth returned HTTP {r.status_code} for {path}.")
            return r.json()["data"]
        raise NexusAuthError("nexusAuth keeps rejecting the access token.")

    def list_all(self, path: str, params: dict | None = None) -> list[dict]:
        items: list[dict] = []
        offset = 0
        while True:
            page = self._get(path, {**(params or {}), "limit": PAGE_SIZE, "offset": offset})
            items.extend(page.get("items", []))
            if not page.get("has_more") or not page.get("items"):
                return items
            offset += PAGE_SIZE

    def download(self, path: str, max_bytes: int) -> bytes:
        """A file nexusAuth serves publicly (an uploaded employee photo), at most max_bytes."""
        try:
            with self._http.stream("GET", path) as r:
                if r.status_code != 200:
                    raise NexusAuthError(f"nexusAuth returned HTTP {r.status_code} for {path}.")
                data = bytearray()
                for chunk in r.iter_bytes():
                    data += chunk
                    if len(data) > max_bytes:
                        raise NexusAuthError(f"{path} is larger than {max_bytes // (1024 * 1024)} MB.")
                return bytes(data)
        except httpx.HTTPError as err:
            raise NexusAuthError(f"Cannot download {path} from nexusAuth ({err.__class__.__name__}).") from None

    def employees(self) -> list[dict]:
        return self.list_all("/api/v1/employees", {"include_exited": "true", "sort_by": "id", "sort_dir": "asc"})

    def companies(self) -> dict[int, str]:
        try:
            rows = self.list_all("/api/v1/companies", {"include_inactive": "true"})
        except NexusAuthError:
            return {}  # company names are optional; employees still sync
        return {c["id"]: c.get("name") for c in rows if "id" in c}


# ----------------------------------------------------------------- mapping --
def _clean(value, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value[:limit] or None


def _clean_address(value) -> str | None:
    if not isinstance(value, str):
        return None
    lines = [" ".join(line.split()) for line in value.splitlines() if line.strip()]
    return "\n".join(lines)[:300] or None


def _valid(fn, value):
    try:
        return fn(value)
    except (ValueError, TypeError):
        return None


def map_employee(remote: dict, companies: dict[int, str]) -> dict:
    """nexusAuth employee JSON -> Signature Studio field values."""
    nexus_id = int(remote["id"])
    first, last = _clean(remote.get("first_name"), 100), _clean(remote.get("last_name"), 100)
    if not first:  # older nexusAuth versions only have full_name
        parts = (_clean(remote.get("full_name"), 200) or "").split(" ", 1)
        first, last = parts[0][:100] or "Employee", (parts[1] if len(parts) > 1 else "")[:100]
    # None = nexusAuth has no Employee ID; the sync then keeps the one already used here.
    code = _valid(v.employee_code, remote.get("employee_code") or "")
    values = {
        "employee_code": code,
        "first_name": first,
        "last_name": last or "",
        "designation": _clean(remote.get("designation"), 150) or _clean(remote.get("job_role"), 150) or "Employee",
        "department": _clean(remote.get("department"), 150),
        "company": _clean(companies.get(remote.get("company_id")), 150),
        "email": str(remote.get("email") or "").strip().lower(),
        "phone": _valid(v.phone, remote.get("phone_number")),
        "linkedin_url": _valid(lambda x: v.http_url(x, field="LinkedIn"), remote.get("linkedin_url")),
        "is_active": remote.get("status") != "exited",
    }
    # Only nexusAuth versions that have an address field send it; an older one never wipes the address here.
    if "address" in remote:
        values["address"] = _clean_address(remote.get("address"))
    return values


# -------------------------------------------------------------------- sync --
@dataclass
class SyncReport:
    started_at: datetime
    finished_at: datetime | None = None
    ok: bool = False
    created: int = 0
    updated: int = 0
    deactivated: int = 0
    unchanged: int = 0
    total_remote: int = 0
    error: str | None = None
    login_rejected: bool = False
    problems: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "started_at": self.started_at, "finished_at": self.finished_at, "ok": self.ok,
            "created": self.created, "updated": self.updated, "deactivated": self.deactivated,
            "unchanged": self.unchanged, "total_remote": self.total_remote,
            "error": self.error, "login_rejected": self.login_rejected, "problems": self.problems[:20],
        }


def _audit(db: Session, action: AuditAction, employee: Employee, text: str) -> None:
    audit_service.record(
        db, action, user_id=None, entity_type="employee", entity_id=employee.id,
        description=f"{text} {employee.full_name} ({employee.employee_code}) from nexusAuth",
    )


def _apply_login(db: Session, employee: Employee) -> None:
    """Keep a linked employee login in step (email and active flag)."""
    user = employee.user
    if user is None or user.role != UserRole.EMPLOYEE:
        return
    user.is_active = employee.is_active
    if user.email != employee.email:
        from app.database.models import User  # local import avoids a cycle at module import

        if db.scalar(select(User.id).where(User.email == employee.email, User.id != user.id)) is None:
            user.email = employee.email


def _sync_photo(employee: Employee, remote: dict, client: NexusAuthClient, report: SyncReport) -> bool:
    """Copy the employee's nexusAuth photo here. Returns True when the photo changed."""
    ref = remote.get("photo_reference")
    ref = ref.strip() if isinstance(ref, str) else ""
    current = employee.profile_photo_url or ""
    if not ref:
        if current.startswith(NEXUS_PHOTO_PREFIX):  # removed in nexusAuth
            employee.profile_photo_url = None
            return True
        return False  # keep a photo added in Signature Studio
    if ref.startswith(("http://", "https://")):  # a hosted image URL: use it as it is
        url = _valid(v.image_ref, ref)
        if url is None or current == url:
            return False
        employee.profile_photo_url = url
        return True
    if not _NEXUS_UPLOAD_PATH.match(ref) or ".." in ref:
        report.problems.append(f"Photo of {employee.email} in nexusAuth was not used: unexpected location {ref!r}.")
        return False
    digest = hashlib.sha256(ref.encode()).hexdigest()[:20]
    storage = storage_service.get_storage()
    if current.startswith(f"{NEXUS_PHOTO_PREFIX}{digest}.") and storage.local_file(current) is not None:
        return False  # already copied and unchanged
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    try:
        data = client.download(ref, max_bytes)
        ext = storage_service.validate_image(data)
    except NexusAuthError as err:
        report.problems.append(f"Photo of {employee.email} could not be copied from nexusAuth: {err}")
        return False
    except AppError as err:
        report.problems.append(f"Photo of {employee.email} in nexusAuth was not used: {err.message}")
        return False
    employee.profile_photo_url = storage.save(data, f"photos/nexus-{digest}.{ext}")
    return True


def _upsert(db: Session, remote: dict, companies: dict[int, str], report: SyncReport,
            client: NexusAuthClient) -> None:
    nexus_id = int(remote["id"])
    values = map_employee(remote, companies)
    if not values["email"]:
        report.problems.append(f"nexusAuth employee #{nexus_id} has no email and was skipped.")
        return

    employee = db.scalar(select(Employee).where(Employee.nexus_employee_id == nexus_id))
    linking = False
    if employee is None:  # first sync: link an existing employee with the same email
        employee = db.scalar(
            select(Employee).where(func.lower(Employee.email) == values["email"], Employee.nexus_employee_id.is_(None))
        )
        linking = employee is not None

    if values["employee_code"] is None:
        values["employee_code"] = employee.employee_code if employee is not None else f"NX-{nexus_id}"
    exclude = employee.id if employee is not None else -1
    other = db.scalar(select(Employee).where(Employee.email == values["email"], Employee.id != exclude))
    if other is not None:
        report.problems.append(
            f"{values['email']} (nexusAuth #{nexus_id}) was skipped: {other.full_name} already uses this email."
        )
        return
    other = db.scalar(select(Employee).where(Employee.employee_code == values["employee_code"], Employee.id != exclude))
    if other is not None:
        wanted, values["employee_code"] = values["employee_code"], f"NX-{nexus_id}"
        if db.scalar(select(Employee.id).where(Employee.employee_code == values["employee_code"], Employee.id != exclude)):
            report.problems.append(f"{values['email']} was skipped: Employee ID {wanted} is already in use.")
            return
        report.problems.append(
            f"Employee ID {wanted} of {values['email']} is already used by {other.full_name}; "
            f"synced as {values['employee_code']}."
        )

    now = utcnow()
    if employee is None:
        employee = Employee(**values, nexus_employee_id=nexus_id, nexus_synced_at=now)
        _sync_photo(employee, remote, client, report)
        db.add(employee)
        db.flush()
        _audit(db, AuditAction.EMPLOYEE_CREATED, employee, "Added")
        report.created += 1
        return

    was_active = employee.is_active
    changed = linking
    for name, value in values.items():
        if getattr(employee, name) != value:
            setattr(employee, name, value)
            changed = True
    employee.nexus_employee_id = nexus_id
    employee.nexus_synced_at = now
    changed = _sync_photo(employee, remote, client, report) or changed
    _apply_login(db, employee)
    if not changed:
        report.unchanged += 1
        return
    if was_active and not employee.is_active:
        _audit(db, AuditAction.EMPLOYEE_DEACTIVATED, employee, "Deactivated")
        report.deactivated += 1
    else:
        _audit(db, AuditAction.EMPLOYEE_UPDATED, employee, "Linked" if linking else "Updated")
        report.updated += 1


def sync_employees(db: Session, client: NexusAuthClient) -> SyncReport:
    report = SyncReport(started_at=utcnow())
    try:
        remote_employees = client.employees()
        companies = client.companies()
    except NexusAuthError as err:
        report.error = str(err)
        report.login_rejected = isinstance(err, NexusAuthLoginRejected)
        report.finished_at = utcnow()
        return report

    report.total_remote = len(remote_employees)
    seen: set[int] = set()
    for remote in remote_employees:
        try:
            seen.add(int(remote["id"]))
            with db.begin_nested():
                _upsert(db, remote, companies, report, client)
        except Exception as err:  # one bad record must not stop the others
            logger.exception("nexusAuth sync failed for employee %s", remote.get("id"))
            report.problems.append(f"nexusAuth employee #{remote.get('id')} could not be synced: {err}")

    # Linked employees that no longer exist in nexusAuth are deactivated, never deleted.
    for employee in db.scalars(select(Employee).where(Employee.nexus_employee_id.is_not(None))).all():
        if employee.nexus_employee_id not in seen and employee.is_active:
            employee.is_active = False
            _apply_login(db, employee)
            _audit(db, AuditAction.EMPLOYEE_DEACTIVATED, employee, "Deactivated (no longer in nexusAuth)")
            report.deactivated += 1

    db.commit()
    report.ok = True
    report.finished_at = utcnow()
    return report


# ----------------------------------------------------- runner and status --
class _State:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.client: NexusAuthClient | None = None
        self.client_key: tuple | None = None
        self.last: SyncReport | None = None
        self.last_success_at: datetime | None = None
        self.rejected_key: tuple | None = None  # credentials nexusAuth refused


_state = _State()


def _client_for_settings() -> NexusAuthClient:
    s = get_settings()
    key = (s.nexusauth_url, s.nexusauth_email, s.nexusauth_password)
    if _state.client is None or _state.client_key != key:
        if _state.client is not None:
            _state.client.close()
        _state.client = NexusAuthClient(*key)
        _state.client_key = key
    return _state.client


def run_sync(db_factory, client: NexusAuthClient | None = None) -> SyncReport:
    """Run one sync (serialised: a manual and a background run never overlap)."""
    with _state.lock:
        db = db_factory()
        try:
            report = sync_employees(db, client or _client_for_settings())
        finally:
            db.close()
        _state.last = report
        _state.rejected_key = _state.client_key if report.login_rejected else None
        if report.ok:
            _state.last_success_at = report.finished_at
        if report.error:
            logger.warning("nexusAuth sync: %s", report.error)
        elif report.created or report.updated or report.deactivated:
            logger.info("nexusAuth sync: %s created, %s updated, %s deactivated",
                        report.created, report.updated, report.deactivated)
        return report


def status() -> dict:
    s = get_settings()
    return {
        "enabled": s.nexus_enabled,
        "url": s.nexusauth_url or None,
        "interval_seconds": s.nexusauth_sync_seconds,
        "synced_fields": [*SYNCED_FIELDS, "profile_photo_url"],
        "last_success_at": _state.last_success_at,
        "paused": _state.rejected_key is not None,
        "last_run": _state.last.as_dict() if _state.last else None,
    }


def start_background_sync(db_factory) -> threading.Event:
    """Start the periodic sync thread; set the returned event to stop it."""
    stop = threading.Event()
    interval = max(5, get_settings().nexusauth_sync_seconds)

    def loop() -> None:
        while not stop.is_set():
            s = get_settings()
            key = (s.nexusauth_url, s.nexusauth_email, s.nexusauth_password)
            try:
                if _state.rejected_key != key:  # don't keep retrying a refused password
                    run_sync(db_factory)
            except Exception:  # never let the thread die
                logger.exception("nexusAuth background sync crashed")
            stop.wait(interval)

    threading.Thread(target=loop, name="nexusauth-sync", daemon=True).start()
    return stop
