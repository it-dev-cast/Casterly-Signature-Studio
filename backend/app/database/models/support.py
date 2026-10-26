"""Supporting tables: revoked JWTs (logout) and global application settings."""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base
from app.database.types import UTCDateTime, utcnow


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)


class AppSettings(Base):
    """Single-row table (id = 1) holding company-wide defaults."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(150), nullable=False, default="Your Company")
    company_website: Mapped[str | None] = mapped_column(String(500))
    # The company logo itself is built into the app (app/branding.py); only its use
    # in email signatures can be switched on or off.
    show_logo_in_signature: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    # Outlook add-in: True (default) = the Signature Studio signature is used in every new email,
    # replacing any signature Outlook put there; False = keep the employee's own Outlook default
    # when one is enabled. Outlook's saved signature settings are never changed either way.
    addin_replace_outlook_signature: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    legal_disclaimer: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, nullable=False
    )


class OutlookAddinStatus(Base):
    """Last thing the Outlook add-in reported for an employee (one row per employee, upserted)."""

    __tablename__ = "outlook_addin_status"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_source: Mapped[str] = mapped_column(String(20), nullable=False)  # auto | button
    last_status: Mapped[str] = mapped_column(String(20), nullable=False)  # inserted | kept_outlook_default | error
    last_detail: Mapped[str | None] = mapped_column(String(500))
    host: Mapped[str | None] = mapped_column(String(100))
    # Name of the signed-in Outlook user (Office.js userProfile.displayName).
    outlook_display_name: Mapped[str | None] = mapped_column(String(200))
    # Whether the employee's own Outlook default signature was enabled (None = unknown).
    outlook_default_enabled: Mapped[bool | None] = mapped_column(Boolean)
    last_inserted_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
