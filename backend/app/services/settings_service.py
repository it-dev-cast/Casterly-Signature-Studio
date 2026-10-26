from sqlalchemy.orm import Session

from app.database.models import AppSettings, AuditAction, User
from app.schemas.misc import SettingsUpdate
from app.services import audit_service

SETTINGS_ID = 1


def get_app_settings(db: Session) -> AppSettings:
    row = db.get(AppSettings, SETTINGS_ID)
    if row is None:
        row = AppSettings(id=SETTINGS_ID, company_name="Your Company")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def update_app_settings(db: Session, data: SettingsUpdate, actor: User) -> AppSettings:
    row = get_app_settings(db)
    logo_toggled = data.show_logo_in_signature != row.show_logo_in_signature
    replace_toggled = data.addin_replace_outlook_signature != row.addin_replace_outlook_signature
    for name, value in data.model_dump().items():
        setattr(row, name, value)
    note = ""
    if logo_toggled:
        note = " (company logo in signatures turned " + ("on)" if row.show_logo_in_signature else "off)")
    if replace_toggled:
        note += (" (Outlook add-in now replaces employees' own default signatures)" if row.addin_replace_outlook_signature
                 else " (Outlook add-in now keeps employees' own default signatures)")
    audit_service.record(
        db, AuditAction.SETTINGS_UPDATED, user_id=actor.id, entity_type="settings",
        entity_id=SETTINGS_ID, description="Updated company settings" + note,
    )
    db.commit()
    db.refresh(row)
    return row
