"""Column types shared by models."""
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """Treat naive datetimes as UTC and normalise aware ones to UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Always stores UTC and always returns timezone-aware UTC datetimes (TIMESTAMP WITH TIME ZONE)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        return as_utc(value)

    def process_result_value(self, value: datetime | None, dialect):
        return as_utc(value)
