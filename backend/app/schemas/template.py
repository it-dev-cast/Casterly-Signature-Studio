from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.renderers import LAYOUTS
from app.schemas.common import ORMModel
from app.utils import validators as v


class TemplateFields(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    layout: str = "classic"
    primary_color: str = "#1F2A44"
    accent_color: str = "#2563EB"
    font_family: str = Field(default="Arial, Helvetica, sans-serif", max_length=120)
    show_photo: bool = True
    show_social: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("layout")
    @classmethod
    def _layout(cls, value: str) -> str:
        if value not in LAYOUTS:
            raise ValueError(f"Unknown layout. Choose one of: {', '.join(LAYOUTS)}.")
        return value

    @field_validator("primary_color", "accent_color")
    @classmethod
    def _color(cls, value: str) -> str:
        return v.hex_color(value)

    @field_validator("font_family")
    @classmethod
    def _font(cls, value: str) -> str:
        # Only allow characters that are safe inside an inline style attribute.
        if not all(c.isalnum() or c in " ,-'" for c in value):
            raise ValueError("Font family contains invalid characters.")
        return value.strip()


class TemplateCreate(TemplateFields):
    pass


class TemplateUpdate(TemplateFields):
    pass


class TemplateRead(ORMModel):
    id: int
    name: str
    description: str | None
    layout: str
    primary_color: str
    accent_color: str
    font_family: str
    show_photo: bool
    show_social: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LayoutInfo(BaseModel):
    key: str
    name: str
    description: str
