from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel
from app.utils import validators as v


class EmployeeFields(BaseModel):
    employee_code: str = Field(min_length=1, max_length=32)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default="", max_length=100)  # optional: some people have a single name
    display_name: str | None = Field(default=None, max_length=200)
    designation: str = Field(min_length=1, max_length=150)
    department: str | None = Field(default=None, max_length=150)
    company: str | None = Field(default=None, max_length=150)
    email: EmailStr
    phone: str | None = None
    mobile: str | None = None
    website: str | None = None
    profile_photo_url: str | None = None
    linkedin_url: str | None = None
    twitter_url: str | None = None
    instagram_url: str | None = None
    other_social_url: str | None = None
    is_active: bool = True

    @field_validator("first_name", "last_name", "designation", mode="before")
    @classmethod
    def _strip_required(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("display_name", "department", "company", mode="before")
    @classmethod
    def _strip_optional(cls, value):
        return v.clean_optional(value) if isinstance(value, str) or value is None else value

    @field_validator("employee_code")
    @classmethod
    def _code(cls, value: str) -> str:
        return v.employee_code(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.lower()

    @field_validator("phone", "mobile")
    @classmethod
    def _phone(cls, value):
        return v.phone(value)

    @field_validator("website")
    @classmethod
    def _website(cls, value):
        return v.website_url(value)

    @field_validator("profile_photo_url")
    @classmethod
    def _photo(cls, value):
        return v.image_ref(value)

    @field_validator("linkedin_url", "twitter_url", "instagram_url", "other_social_url")
    @classmethod
    def _social(cls, value):
        return v.http_url(value, field="Social link")


class EmployeeCreate(EmployeeFields):
    # Optional: set a password to give the employee a login account.
    password: str | None = Field(default=None, min_length=8, max_length=128)


class EmployeeUpdate(EmployeeFields):
    # Optional: set to create a login or reset the existing password.
    password: str | None = Field(default=None, min_length=8, max_length=128)


class EmployeeStatusUpdate(BaseModel):
    is_active: bool


class EmployeeRead(ORMModel):
    id: int
    employee_code: str
    user_id: int | None
    first_name: str
    last_name: str
    display_name: str | None
    full_name: str
    designation: str
    department: str | None
    company: str | None
    email: str
    phone: str | None
    mobile: str | None
    website: str | None
    address: str | None = None  # read-only here: set only by the nexusAuth sync
    profile_photo_url: str | None
    linkedin_url: str | None
    twitter_url: str | None
    instagram_url: str | None
    other_social_url: str | None
    is_active: bool
    has_login: bool
    managed_by_nexus: bool = False
    nexus_employee_id: int | None = None
    nexus_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
