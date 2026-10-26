"""The company logo, built into the application.

Signature Studio is for Casterly's internal use, so the logo is a fixed asset that
ships with the code (app/static/brand/) rather than an editable upload. Admins can
only choose whether it appears in email signatures (AppSettings.show_logo_in_signature).
To change the logo, replace the file below and redeploy.
"""
from functools import lru_cache
from pathlib import Path

from PIL import Image

STATIC_DIR = Path(__file__).resolve().parent / "static"
LOGO_FILE = STATIC_DIR / "brand" / "casterly-logo.png"
LOGO_PATH = "/static/brand/casterly-logo.png"  # public path, served by FastAPI

# In signatures the logo is fitted into this box, keeping its aspect ratio.
LOGO_MAX_WIDTH = 50
LOGO_MAX_HEIGHT = 50


@lru_cache
def logo_display_size() -> tuple[int, int]:
    """(width, height) in px for the logo in signatures. Outlook needs explicit sizes."""
    with Image.open(LOGO_FILE) as img:
        w, h = img.size
    scale = min(LOGO_MAX_WIDTH / w, LOGO_MAX_HEIGHT / h)
    return max(1, round(w * scale)), max(1, round(h * scale))
