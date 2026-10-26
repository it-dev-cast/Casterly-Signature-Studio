from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base
from app.database.models.enums import UserRole
from app.database.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.database.models.employee import Employee


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20), nullable=False, default=UserRole.EMPLOYEE
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employee: Mapped["Employee | None"] = relationship(back_populates="user", uselist=False)
