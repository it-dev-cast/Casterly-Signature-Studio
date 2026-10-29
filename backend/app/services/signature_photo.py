"""Round, signature-sized copies of employee photos.

Classic Outlook for Windows (Word rendering engine) ignores border-radius and object-fit and
can't show WebP, so the photo in a signature must already be the final picture: a square PNG,
cut to a circle with transparent corners. It is made once per uploaded photo and stored next
to the originals (photos/sig/), so the add-in can ask for a signature on every email cheaply.
"""
import io
import logging
from pathlib import PurePosixPath

from PIL import Image, ImageDraw, ImageOps

from app.services.storage_service import get_storage

logger = logging.getLogger(__name__)

SIZE = 128  # pixels in the file: twice the 64px shown, so it stays sharp on high-DPI screens
SUPERSAMPLE = 4  # the circle is drawn this much larger, then scaled down for a smooth edge


def round_photo_png(data: bytes) -> bytes:
    """The photo centre-cropped to a square, scaled to SIZE and cut to a circle, as PNG."""
    with Image.open(io.BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img).convert("RGBA")
        square = ImageOps.fit(img, (SIZE, SIZE), Image.LANCZOS)
    big = SIZE * SUPERSAMPLE
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, big - 1, big - 1), fill=255)
    square.putalpha(mask.resize((SIZE, SIZE), Image.LANCZOS))
    buf = io.BytesIO()
    square.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def signature_photo_path(stored: str | None) -> str | None:
    """The round copy's public path for a stored photo, made on first use.

    Photos hosted elsewhere (full http(s) URLs) or missing files are returned unchanged.
    """
    storage = get_storage()
    source = storage.local_file(stored) if stored else None
    if source is None:
        return stored
    # The source's modification time is part of the name, so a replaced file gets a new copy
    # (and a new URL, which Outlook's image cache has never seen).
    stem = PurePosixPath(stored).stem
    key = f"photos/sig/{stem}-{source.stat().st_mtime_ns}.png"
    public = f"/uploads/{key}"
    if storage.local_file(public) is not None:
        return public
    try:
        return storage.save(round_photo_png(source.read_bytes()), key)
    except Exception:  # an unreadable photo must not break the signature
        logger.exception("Could not make a round signature photo from %s", stored)
        return stored
