from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.database.models import BannerStatus
from app.database.types import as_utc
from app.schemas.common import ORMModel
from app.utils import validators as v


class BannerFields(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    image_url: str
    target_url: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

    @field_validator("name", "title", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("description", mode="before")
    @classmethod
    def _desc(cls, value):
        return v.clean_optional(value) if isinstance(value, str) or value is None else value

    @field_validator("image_url", mode="before")
    @classmethod
    def _image(cls, value):
        return v.image_ref(value, required=True)

    @field_validator("target_url")
    @classmethod
    def _target(cls, value):
        return v.http_url(value, field="Target URL")

    @field_validator("start_date", "end_date")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        # Naive datetimes are interpreted as UTC; everything is stored as UTC.
        return as_utc(value)

    @model_validator(mode="after")
    def _date_range(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("End date must be after the start date.")
        return self


class BannerCreate(BannerFields):
    pass


class BannerUpdate(BannerFields):
    pass


class BannerPreviewRequest(BannerFields):
    """Render a banner that has not been saved yet."""


class BannerRead(ORMModel):
    id: int
    name: str
    title: str
    description: str | None
    image_url: str
    image_public_url: str
    target_url: str | None
    status: BannerStatus
    effective_status: BannerStatus
    is_current: bool
    start_date: datetime | None
    end_date: datetime | None
    published_at: datetime | None
    created_by: int | None
    created_by_email: str | None
    created_at: datetime
    updated_at: datetime


class BannerWithHtml(BannerRead):
    html: str


class BannerHtml(BaseModel):
    html: str


class CurrentBanner(BaseModel):
    banner: BannerWithHtml | None
