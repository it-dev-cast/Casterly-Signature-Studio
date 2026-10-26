"""employee address

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.add_column(sa.Column("address", sa.String(length=300), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_column("address")
