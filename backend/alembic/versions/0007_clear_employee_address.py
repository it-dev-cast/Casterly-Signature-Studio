"""clear synced employee addresses

The old office addresses were removed in nexusAuth (employees now pick one of the new
office addresses there). This clears the stale copies here; the next nexusAuth sync
fills in each employee's current address.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-05

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE employees SET address = NULL")


def downgrade() -> None:
    pass  # the removed addresses cannot be restored
