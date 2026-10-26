from typing import TYPE_CHECKING

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base
from app.database.models.mixins import TimestampMixin
from app.database.types import UTCDateTime

if TYPE_CHECKING:
    from app.database.models.user import User


class Employee(TimestampMixin, Base):
    """Personal signature data only. The company banner is NEVER stored here."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    designation: Mapped[str] = mapped_column(String(150), nullable=False)
    department: Mapped[str | None] = mapped_column(String(150), index=True)
    company: Mapped[str | None] = mapped_column(String(150))

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    mobile: Mapped[str | None] = mapped_column(String(40))
    website: Mapped[str | None] = mapped_column(String(500))
    address: Mapped[str | None] = mapped_column(String(300))
    profile_photo_url: Mapped[str | None] = mapped_column(String(500))

    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    twitter_url: Mapped[str | None] = mapped_column(String(500))
    instagram_url: Mapped[str | None] = mapped_column(String(500))
    other_social_url: Mapped[str | None] = mapped_column(String(500))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    # Set when this employee is kept in sync from nexusAuth (the nexusAuth employee id).
    # nexusAuth then owns the synced fields; see services/nexus_sync.py.
    nexus_employee_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True, nullable=True)
    nexus_synced_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    user: Mapped["User | None"] = relationship(back_populates="employee")

    @property
    def full_name(self) -> str:
        return self.display_name or f"{self.first_name} {self.last_name}".strip()

    @property
    def managed_by_nexus(self) -> bool:
        return self.nexus_employee_id is not None

    @property
    def has_login(self) -> bool:
        return self.user_id is not None
