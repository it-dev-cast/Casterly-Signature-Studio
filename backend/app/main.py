import logging
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from app import branding
from app.api import (
    audit, auth, banners, employees, installer, integrations, live_banner, outlook_addin, overview, settings, setup, signatures,
    templates, uploads,
)
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.database.database import SessionLocal
from app.services import nexus_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app() -> FastAPI:
    config = get_settings()
    outlook_addin.warn_if_unusable_public_url()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Keep employees in sync with nexusAuth while the server runs (if configured).
        stop = nexus_sync.start_background_sync(SessionLocal) if config.nexus_enabled else None
        yield
        if stop is not None:
            stop.set()

    # Docs are served by hand so they work behind a proxy that strips a sub-path (ROOT_PATH).
    # FastAPI's own root_path would also break the StaticFiles mounts in that setup.
    app = FastAPI(title=config.app_name, version="1.0.0", docs_url=None, openapi_url="/api/openapi.json",
                  lifespan=lifespan)

    @app.get("/api/docs", include_in_schema=False)
    def docs():
        return get_swagger_ui_html(openapi_url=f"{config.root_path.rstrip('/')}/api/openapi.json",
                                   title=f"{config.app_name} - API docs")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Content-Disposition", "X-Casterly-Signature-Mode"],
    )
    register_exception_handlers(app)

    api = APIRouter(prefix="/api")
    for module in (auth, employees, banners, installer, signatures, templates, overview, audit, settings, uploads,
                   integrations):
        api.include_router(module.router)
    api.include_router(settings.branding_router)
    api.include_router(installer.public_router)
    api.include_router(setup.admin_router)
    api.include_router(outlook_addin.admin_router)

    @api.get("/health", tags=["health"])
    def health():
        return {"success": True, "data": {"status": "ok"}}

    app.include_router(api)
    app.include_router(live_banner.router)  # public /banner/current(.png)
    app.include_router(outlook_addin.router)  # public Outlook add-in files + signature
    app.include_router(setup.public_router)  # public /setup/<key> page for employees

    upload_dir = Path(config.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")
    app.mount("/static", StaticFiles(directory=branding.STATIC_DIR), name="static")
    return app


app = create_app()
