from sqlalchemy import Boolean, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base
from app.database.models.mixins import TimestampMixin


class SignatureTemplate(TimestampMixin, Base):
    """A reusable signature design.

    `layout` selects a renderer from app.renderers.LAYOUTS; the remaining fields
    are style options passed to that renderer. New designs = new renderer + row.
    """

    __tablename__ = "signature_templates"
    __table_args__ = (
        # At most one active template, enforced by the database.
        Index(
            "uq_signature_templates_single_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    layout: Mapped[str] = mapped_column(String(40), nullable=False, default="classic")
    primary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#1F2A44")
    accent_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#2563EB")
    font_family: Mapped[str] = mapped_column(
        String(120), nullable=False, default="Arial, Helvetica, sans-serif"
    )
    show_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_social: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
