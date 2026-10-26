"""outlook add-in status + replace-signature setting

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("app_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("addin_replace_outlook_signature", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    op.create_table(
        "outlook_addin_status",
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_source", sa.String(length=20), nullable=False),
        sa.Column("last_status", sa.String(length=20), nullable=False),
        sa.Column("last_detail", sa.String(length=500), nullable=True),
        sa.Column("host", sa.String(length=100), nullable=True),
        sa.Column("outlook_default_enabled", sa.Boolean(), nullable=True),
        sa.Column("last_inserted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("employee_id"),
    )


def downgrade() -> None:
    op.drop_table("outlook_addin_status")
    with op.batch_alter_table("app_settings", schema=None) as batch_op:
        batch_op.drop_column("addin_replace_outlook_signature")
