from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import branding
from app.core.config import get_settings as get_config
from app.core.dependencies import require_admin
from app.database.database import get_db
from app.database.models import AppSettings, User
from app.schemas.common import ApiResponse, ok
from app.schemas.misc import BrandingRead, SettingsRead, SettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])

# Public: company name + logo are shown on the login page before anyone signs in.
branding_router = APIRouter(prefix="/branding", tags=["settings"])


def _read(row: AppSettings) -> dict:
    return {
        "company_name": row.company_name,
        "company_website": row.company_website,
        "legal_disclaimer": row.legal_disclaimer,
        "show_logo_in_signature": row.show_logo_in_signature,
        "addin_replace_outlook_signature": row.addin_replace_outlook_signature,
        "company_logo_url": branding.LOGO_PATH,  # the app loads it from its own server
        "public_base_url": get_config().public_base_url,
        "updated_at": row.updated_at,
    }


@router.get("", response_model=ApiResponse[SettingsRead])
def get_settings(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return ok(_read(settings_service.get_app_settings(db)))


@router.put("", response_model=ApiResponse[SettingsRead])
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return ok(_read(settings_service.update_app_settings(db, body, admin)))


@branding_router.get("", response_model=ApiResponse[BrandingRead])
def get_branding(db: Session = Depends(get_db)):
    row = settings_service.get_app_settings(db)
    return ok({
        "company_name": row.company_name,
        "company_logo_url": branding.LOGO_PATH,  # the app loads it from its own server
        # Public address used in emails; previews swap it for the app's own so they work without it.
        "public_base_url": get_config().public_base_url,
    })
