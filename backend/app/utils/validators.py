"""Reusable field validators for Pydantic schemas."""
import re
from urllib.parse import urlparse

_PHONE_RE = re.compile(r"^\+?[0-9()\-.\s]{5,30}$")
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,31}$")


def clean_optional(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


def http_url(v: str | None, *, field: str = "URL") -> str | None:
    """Require an absolute http(s) URL (or None)."""
    v = clean_optional(v)
    if v is None:
        return None
    if len(v) > 500:
        raise ValueError(f"{field} is too long.")
    parsed = urlparse(v)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or " " in v:
        raise ValueError(f"{field} must be a valid http(s) URL.")
    return v


def website_url(v: str | None) -> str | None:
    """Accept 'example.com' and normalise it to 'https://example.com'."""
    v = clean_optional(v)
    if v is None:
        return None
    if not re.match(r"^https?://", v, re.I):
        v = f"https://{v}"
    return http_url(v, field="Website")


def image_ref(v: str | None, *, required: bool = False) -> str | None:
    """An image is either an absolute http(s) URL or a path we serve under /uploads/."""
    v = clean_optional(v)
    if v is None:
        if required:
            raise ValueError("An image is required.")
        return None
    if v.startswith("/uploads/"):
        if ".." in v or "\\" in v:
            raise ValueError("Invalid image path.")
        return v
    return http_url(v, field="Image URL")


def phone(v: str | None) -> str | None:
    v = clean_optional(v)
    if v is None:
        return None
    if not _PHONE_RE.match(v) or sum(c.isdigit() for c in v) < 5:
        raise ValueError("Enter a valid phone number (digits, spaces, +, -, parentheses).")
    return v


def hex_color(v: str) -> str:
    v = v.strip()
    if not _HEX_RE.match(v):
        raise ValueError("Colour must be a hex value like #1F2A44.")
    return v.upper()


def employee_code(v: str) -> str:
    v = v.strip()
    if not _CODE_RE.match(v):
        raise ValueError("Employee ID may contain letters, numbers, '-' and '_' (max 32).")
    return v.upper()
