"""Add reminder_sent_at to subscriptions

Revision ID: 6_add_subs_reminder_at
Revises: 5_add_selected_plan
Create Date: 2026-02-24 18:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6_add_subs_reminder_at"
down_revision: Union[str, Sequence[str], None] = "5_add_selected_plan"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "reminder_sent_at")

