"""create hmrc submissions (audit trail)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-08

Append-only record of every attempt to send figures to HMRC: exactly what was sent,
and exactly what HMRC replied. RESTRICT on the landlord: filing history must outlive
everything else.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hmrc_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("landlord_id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.String(length=32), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("consolidated_expenses", sa.Boolean(), nullable=False),
        sa.Column("request_body", sa.JSON(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("hmrc_correlation_id", sa.String(length=64), nullable=True),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["landlord_id"],
            ["landlords.id"],
            name="fk_hmrc_submissions_landlord_id_landlords",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_hmrc_submissions"),
    )
    op.create_index("ix_hmrc_submissions_landlord_id", "hmrc_submissions", ["landlord_id"])


def downgrade() -> None:
    op.drop_index("ix_hmrc_submissions_landlord_id", table_name="hmrc_submissions")
    op.drop_table("hmrc_submissions")
