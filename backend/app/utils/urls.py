import ipaddress
from urllib.parse import urlparse

from app.core.config import get_settings


def resolve_public_url(value: str | None) -> str | None:
    """Turn a stored image reference into an absolute, HTTP-accessible URL.

    Uploaded files are stored as '/uploads/...' paths so that changing
    PUBLIC_BASE_URL (e.g. on deployment) updates every generated signature.
    """
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return f"{get_settings().public_base_url}/{value.lstrip('/')}"


def outlook_url_problem(base: str) -> str | None:
    """Why Outlook can't load the add-in from this PUBLIC_BASE_URL, or None if it can.

    Outlook loads every add-in file (manifest, commands.html, launchevent.js, icons) and the
    signature itself from this address, and only accepts https:// hosts. https://localhost is
    allowed for testing on the developer's own PC (with Microsoft's trusted dev certificate,
    `npx office-addin-dev-certs install`); everyone else needs a public https:// host.
    """
    parsed = urlparse(base)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        return "it is not an https:// address"
    if host in ("localhost", "127.0.0.1"):
        return None  # local testing only: works in Outlook on this PC
    if host.endswith((".localhost", ".local")):
        return "it is a local address that Outlook cannot reach"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return None
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        return "it is a private network address that Outlook cannot reach"
    return None


def is_temporary_tunnel(base: str) -> bool:
    """Cloudflare "quick tunnel" addresses change every time the tunnel restarts."""
    return (urlparse(base).hostname or "").lower().endswith(".trycloudflare.com")
