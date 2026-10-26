"""Schemas for signatures, overview, audit logs, settings and uploads."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.banner import BannerWithHtml
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeRead
from app.schemas.template import TemplateRead
from app.utils import validators as v


class SignatureRead(BaseModel):
    employee: EmployeeRead
    template: TemplateRead | None
    banner: BannerWithHtml | None
    html: str  # preview version: shows the current banner image directly
    live_html: str  # copy/paste version: banner always shows whatever is published
    generated_at: datetime


class OverviewStats(BaseModel):
    total_employees: int
    active_employees: int
    draft_banners: int
    signature_templates: int
    has_published_banner: bool


class OverviewRead(BaseModel):
    stats: OverviewStats
    current_banner: BannerWithHtml | None
    active_template: TemplateRead | None


class AuditLogRead(ORMModel):
    id: int
    user_id: int | None
    user_email: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    description: str | None
    created_at: datetime


class SettingsRead(ORMModel):
    company_name: str
    company_website: str | None
    legal_disclaimer: str | None
    show_logo_in_signature: bool
    addin_replace_outlook_signature: bool
    company_logo_url: str  # built-in logo, path on this server, read-only
    public_base_url: str  # where Outlook and email recipients load everything from
    updated_at: datetime


class SettingsUpdate(BaseModel):
    company_name: str = Field(min_length=1, max_length=150)
    company_website: str | None = None
    legal_disclaimer: str | None = Field(default=None, max_length=1000)
    show_logo_in_signature: bool = True
    addin_replace_outlook_signature: bool = True

    @field_validator("company_name", mode="before")
    @classmethod
    def _name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("company_website")
    @classmethod
    def _site(cls, value):
        return v.website_url(value)

    @field_validator("legal_disclaimer", mode="before")
    @classmethod
    def _disc(cls, value):
        return v.clean_optional(value) if isinstance(value, str) or value is None else value


class BrandingRead(BaseModel):
    """Public company branding (shown on the login page and in the app header)."""

    company_name: str
    company_logo_url: str  # path of the built-in logo on this server
    public_base_url: str  # address used for images in emails


class UploadRead(BaseModel):
    path: str
    url: str
