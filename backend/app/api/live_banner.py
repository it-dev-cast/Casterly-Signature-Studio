"""Public, fixed addresses for "whatever banner is published right now".

Signatures installed into Outlook embed these URLs instead of a specific banner, so
publishing, replacing or unpublishing a banner changes them with no reinstall:

    GET /banner/current.png   the current banner image (or an invisible strip if none)
    GET /banner/current       redirects to the current banner's target URL

They must be public: email clients load images without any login.
"""
import io
from functools import lru_cache

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from PIL import Image
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.renderers.html_utils import e
from app.services import banner_service, settings_service
from app.services.storage_service import get_storage

router = APIRouter(prefix="/banner", tags=["live banner"])

# Email clients should check back rather than keep an old banner forever.
NO_STORE = {"Cache-Control": "no-cache, max-age=0, must-revalidate"}


@lru_cache
def _blank_png() -> bytes:
    # Transparent and very wide: at the signature's width it collapses to a 1px strip.
    buf = io.BytesIO()
    Image.new("RGBA", banner_service.BLANK_BANNER_SIZE, (255, 255, 255, 0)).save(buf, format="PNG")
    return buf.getvalue()


@lru_cache(maxsize=8)
def _as_png(path: str, mtime_ns: int) -> bytes:
    """A WebP or GIF banner converted to PNG (classic Outlook can't show WebP). Cached per file
    version, since this address is loaded for every email opened."""
    with Image.open(path) as img:
        buf = io.BytesIO()
        img.convert("RGBA").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


@router.get("/current.png")
def current_banner_image(db: Session = Depends(get_db)):
    banner = banner_service.get_current_published_banner(db)
    if banner is None:
        return Response(_blank_png(), media_type="image/png", headers=NO_STORE)
    etag = f'"banner-{banner.id}-{int(banner.updated_at.timestamp())}"'
    local = get_storage().local_file(banner.image_url)
    if local is not None:
        if local.suffix.lower() in (".png", ".jpg", ".jpeg"):
            return FileResponse(local, headers={**NO_STORE, "ETag": etag})
        png = _as_png(str(local), local.stat().st_mtime_ns)
        return Response(png, media_type="image/png", headers={**NO_STORE, "ETag": etag})
    # Externally hosted image: send the client there.
    return RedirectResponse(banner.image_url, status_code=302, headers=NO_STORE)


@router.get("/current")
def current_banner_link(db: Session = Depends(get_db)):
    banner = banner_service.get_current_published_banner(db)
    app_settings = settings_service.get_app_settings(db)
    target = (banner.target_url if banner else None) or app_settings.company_website
    if target:
        return RedirectResponse(target, status_code=302, headers=NO_STORE)
    return HTMLResponse(
        f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{e(app_settings.company_name)}</title></head>"
        f"<body style='font-family:Arial,sans-serif;padding:40px;color:#374151'><h1>{e(app_settings.company_name)}</h1>"
        "<p>There is no current campaign.</p></body></html>",
        headers=NO_STORE,
    )
