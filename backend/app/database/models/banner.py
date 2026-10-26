from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base
from app.database.models.enums import BannerStatus
from app.database.models.mixins import TimestampMixin
from app.database.models.user import User
from app.database.types import UTCDateTime


class Banner(TimestampMixin, Base):
    """A company-wide banner. Only ONE row may be PUBLISHED at a time (DB-enforced)."""

    __tablename__ = "banners"
    __table_args__ = (
        Index(
            "uq_banners_single_published",
            "status",
            unique=True,
            postgresql_where=text("status = 'PUBLISHED'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    target_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[BannerStatus] = mapped_column(
        Enum(BannerStatus, native_enum=False, length=20),
        nullable=False,
        default=BannerStatus.DRAFT,
        index=True,
    )
    start_date: Mapped[datetime | None] = mapped_column(UTCDateTime())
    end_date: Mapped[datetime | None] = mapped_column(UTCDateTime())
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    creator: Mapped[User | None] = relationship(lazy="joined")
