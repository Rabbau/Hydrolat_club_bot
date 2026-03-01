"""Add unique active subscription per user

Revision ID: 7_uq_active_sub
Revises: 6_add_subs_reminder_at
Create Date: 2026-03-01 19:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7_uq_active_sub"
down_revision: Union[str, Sequence[str], None] = "6_add_subs_reminder_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Resolve pre-existing duplicates deterministically before adding unique index.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id
                    ORDER BY COALESCE(updated_at, created_at) DESC, id DESC
                ) AS rn
            FROM subscriptions
            WHERE status = 'active'
        )
        UPDATE subscriptions s
        SET status = 'cancelled',
            updated_at = NOW()
        FROM ranked r
        WHERE s.id = r.id
          AND r.rn > 1
        """
    )

    op.create_index(
        "uq_subscriptions_user_active",
        "subscriptions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_subscriptions_user_active", table_name="subscriptions")
