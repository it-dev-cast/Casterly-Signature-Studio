"""Public gateway: ONLY the routes Outlook and email recipients need.

Put this app (not app.main) on the internet, e.g. behind a tunnel or reverse proxy:

    uvicorn app.public_app:app --port 8001

It serves the Outlook add-in files, signatures by email for active employees, the live
banner, the built-in logo and uploaded images. There is no login, no admin API and no
employee management here, so exposing it does not expose Signature Studio itself.
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import branding
from app.api import installer, live_banner, outlook_addin, setup
from app.core.config import get_settings
from app.core.errors import register_exception_handlers


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_public_app() -> FastAPI:
    config = get_settings()
    outlook_addin.warn_if_unusable_public_url()
    app = FastAPI(title=f"{config.app_name} (public)", docs_url=None, redoc_url=None, openapi_url=None)
    # Outlook's add-in runtimes call these endpoints from their own origins; read-only, no credentials.
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"],
        expose_headers=["X-Casterly-Signature-Mode"],
    )
    register_exception_handlers(app)

    app.include_router(outlook_addin.router)
    app.include_router(live_banner.router)
    app.include_router(installer.public_router, prefix="/api")
    app.include_router(setup.public_router)

    @app.get("/api/health", include_in_schema=False)
    def health():
        return {"success": True, "data": {"status": "ok", "gateway": "public"}}

    upload_dir = Path(config.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")
    app.mount("/static", StaticFiles(directory=branding.STATIC_DIR), name="static")
    return app


app = create_public_app()
