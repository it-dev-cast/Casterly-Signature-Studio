"""company logo switch

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("app_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("show_logo_in_signature", sa.Boolean(), nullable=False, server_default=sa.true())
        )


def downgrade() -> None:
    with op.batch_alter_table("app_settings", schema=None) as batch_op:
        batch_op.drop_column("show_logo_in_signature")
