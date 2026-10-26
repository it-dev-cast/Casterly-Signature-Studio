from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base
from app.database.models.user import User
from app.database.types import UTCDateTime, utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(40), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, nullable=False, index=True
    )

    user: Mapped[User | None] = relationship()
