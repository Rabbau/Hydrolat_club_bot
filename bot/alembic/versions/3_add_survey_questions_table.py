"""Add survey_questions table

Revision ID: 3_add_survey_questions_table
Revises: 2_add_payment_survey_tables
Create Date: 2026-02-16 17:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3_add_survey_questions_table"
down_revision: Union[str, Sequence[str], None] = "2_add_payment_survey_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "survey_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=50), nullable=False, server_default="text"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("position"),
    )


def downgrade() -> None:
    op.drop_table("survey_questions")
