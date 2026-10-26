"""outlook add-in uses the Signature Studio signature by default; store Outlook user name

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("app_settings", schema=None) as batch_op:
        batch_op.alter_column("addin_replace_outlook_signature", server_default=sa.true())
    # The previous default ("keep the employee's own default") made the add-in skip inserting;
    # the Signature Studio signature is now used in every new email.
    op.execute(sa.text("UPDATE app_settings SET addin_replace_outlook_signature = :v").bindparams(v=True))
    with op.batch_alter_table("outlook_addin_status", schema=None) as batch_op:
        batch_op.add_column(sa.Column("outlook_display_name", sa.String(length=200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("outlook_addin_status", schema=None) as batch_op:
        batch_op.drop_column("outlook_display_name")
    with op.batch_alter_table("app_settings", schema=None) as batch_op:
        batch_op.alter_column("addin_replace_outlook_signature", server_default=sa.false())
