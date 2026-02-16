"""Add promo fields to survey_submissions

Revision ID: 4_add_promo_cols
Revises: 3_add_survey_questions_table
Create Date: 2026-02-16 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4_add_promo_cols"
down_revision: Union[str, Sequence[str], None] = "3_add_survey_questions_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "survey_submissions",
        sa.Column("promo_code_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "survey_submissions",
        sa.Column("promo_discount", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_survey_submissions_promo_code_id",
        "survey_submissions",
        "promo_codes",
        ["promo_code_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_survey_submissions_promo_code_id",
        "survey_submissions",
        type_="foreignkey",
    )
    op.drop_column("survey_submissions", "promo_discount")
    op.drop_column("survey_submissions", "promo_code_id")
