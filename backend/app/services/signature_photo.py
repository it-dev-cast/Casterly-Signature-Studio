"""Square, signature-sized copies of employee photos.

Classic Outlook for Windows (Word rendering engine) ignores object-fit and can't show WebP, so
the photo in a signature must already be the final picture: a square PNG, solid (no
transparency), with the whole photo fitted inside it - never cropped. It is made once per
uploaded photo and stored next to the originals (photos/sig/), so the add-in can ask for a
signature on every email cheaply.
"""
import io
import logging
from pathlib import PurePosixPath

from PIL import Image, ImageOps

from app.services.storage_service import get_storage

logger = logging.getLogger(__name__)

SIZE = 128  # pixels in the file: twice the 64px shown, so it stays sharp on high-DPI screens
BACKGROUND = (255, 255, 255)  # padding around a photo that isn't square, and behind transparency
# Part of every copy's file name. Change it whenever the picture's look changes, so no old copy
# is reused and Outlook / Microsoft's image proxy fetch the new one instead of a cached image.
STYLE = "sq2"


def square_photo_png(data: bytes) -> bytes:
    """The whole photo scaled to fit a SIZE square (aspect ratio kept), centred on white, as PNG."""
    with Image.open(io.BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img).convert("RGBA")
        fitted = ImageOps.contain(img, (SIZE, SIZE), Image.LANCZOS)
    square = Image.new("RGB", (SIZE, SIZE), BACKGROUND)
    square.paste(fitted, ((SIZE - fitted.width) // 2, (SIZE - fitted.height) // 2), mask=fitted)
    buf = io.BytesIO()
    square.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def signature_photo_path(stored: str | None) -> str | None:
    """The square copy's public path for a stored photo, made on first use.

    Photos hosted elsewhere (full http(s) URLs) or missing files are returned unchanged.
    """
    storage = get_storage()
    source = storage.local_file(stored) if stored else None
    if source is None:
        return stored
    # The source's modification time is part of the name, so a replaced file gets a new copy
    # (and a new URL, which Outlook's image cache has never seen).
    stem = PurePosixPath(stored).stem
    key = f"photos/sig/{stem}-{source.stat().st_mtime_ns}-{STYLE}.png"
    public = f"/uploads/{key}"
    if storage.local_file(public) is not None:
        return public
    try:
        return storage.save(square_photo_png(source.read_bytes()), key)
    except Exception:  # an unreadable photo must not break the signature
        logger.exception("Could not make a signature photo from %s", stored)
        return stored
