"""Add selected_plan_id to survey_submissions

Revision ID: 5_add_selected_plan
Revises: 4_add_promo_cols
Create Date: 2026-02-17 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "5_add_selected_plan"
down_revision: Union[str, Sequence[str], None] = "4_add_promo_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "survey_submissions",
        sa.Column("selected_plan_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_survey_submissions_selected_plan_id",
        "survey_submissions",
        "payment_plans",
        ["selected_plan_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_survey_submissions_selected_plan_id",
        "survey_submissions",
        type_="foreignkey",
    )
    op.drop_column("survey_submissions", "selected_plan_id")
