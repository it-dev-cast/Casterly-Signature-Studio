"""link employees to nexusAuth for automatic sync

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.add_column(sa.Column("nexus_employee_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("nexus_synced_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_employees_nexus_employee_id", ["nexus_employee_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_index("ix_employees_nexus_employee_id")
        batch_op.drop_column("nexus_synced_at")
        batch_op.drop_column("nexus_employee_id")
