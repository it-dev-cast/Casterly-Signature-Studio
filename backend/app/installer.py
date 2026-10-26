"""Outlook signature installer support.

Each employee downloads the SAME Windows program (app/installer/CasterlySignatureSetup.exe);
only its file name differs. The name carries an installation key:

    Casterly-Signature-Setup_<server-url-base64url>.<employee-id>.<hmac>.exe

When run, the program reads its own file name, calls GET /api/installer/signature with the
key, and writes the returned HTML into classic Outlook's signature folder. Keeping the
executable byte-identical means it can be code-signed once.

The installed signature uses the *live* banner URLs (/banner/current.png and
/banner/current), so publishing a new banner updates it without reinstalling.
"""
import base64
import hashlib
import hmac
from pathlib import Path

from app.core.config import get_settings

INSTALLER_FILE = Path(__file__).resolve().parent / "installer" / "CasterlySignatureSetup.exe"
FILE_PREFIX = "Casterly-Signature-Setup"
SIGNATURE_NAME = "Casterly signature"  # the name the signature gets inside Outlook


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def employee_key_signature(employee_id: int) -> str:
    mac = hmac.new(get_settings().secret_key.encode(), f"sig-installer:{employee_id}".encode(), hashlib.sha256)
    return _b64url(mac.digest()[:18])


def verify_key(employee_id: int, signature: str) -> bool:
    return hmac.compare_digest(employee_key_signature(employee_id), signature)


def installer_filename(employee_id: int) -> str:
    server = _b64url(get_settings().public_base_url.encode())
    return f"{FILE_PREFIX}_{server}.{employee_id}.{employee_key_signature(employee_id)}.exe"
