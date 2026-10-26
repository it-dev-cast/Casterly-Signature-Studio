"""Application configuration loaded from environment variables / .env."""
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Signature Studio"
    environment: str = "development"

    # Required. PostgreSQL only: postgresql+psycopg://user:pass@host:5432/dbname
    database_url: str

    # Required - intentionally no default so secrets are never hardcoded.
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    remember_me_expire_days: int = 7

    # Absolute base URL used for every image inside generated email HTML.
    public_base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173"
    # Sub-path a reverse proxy publishes the app under (and strips), e.g. "/signature". Only used by /api/docs.
    root_path: str = ""

    upload_dir: str = "uploads"
    max_upload_mb: int = 5

    # Outgoing email for "Send email" (signature setup emails). Leave SMTP_HOST empty to
    # disable automatic sending; the app then offers to open the email in your mail app.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""  # e.g. "Casterly Signatures <signatures@casterly.com>"
    smtp_security: str = "starttls"  # starttls | ssl | none

    # nexusAuth employee sync. Signature Studio signs in to nexusAuth with this account
    # (role operator or admin) and copies its employees here. Leave NEXUSAUTH_URL empty to disable.
    nexusauth_url: str = ""  # e.g. http://127.0.0.1:8000
    nexusauth_email: str = ""
    nexusauth_password: str = ""
    nexusauth_sync_seconds: int = 30

    @property
    def nexus_enabled(self) -> bool:
        return bool(self.nexusauth_url and self.nexusauth_email and self.nexusauth_password)

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and (self.smtp_from or self.smtp_username))

    @field_validator("database_url")
    @classmethod
    def _postgres_only(cls, v: str) -> str:
        v = v.strip()
        # Plain postgresql:// / postgres:// would pick the psycopg2 driver, which isn't installed.
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                v = "postgresql+psycopg://" + v[len(prefix):]
        if not v.startswith("postgresql+psycopg://"):
            raise ValueError(
                "Signature Studio uses PostgreSQL only. Set DATABASE_URL to "
                "postgresql+psycopg://user:password@host:5432/signature_studio"
            )
        return v

    @field_validator("public_base_url")
    @classmethod
    def _public_base_url(cls, v: str) -> str:
        return v.rstrip("/")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
