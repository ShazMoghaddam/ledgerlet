"""create properties table

Revision ID: 0001
Revises:
Create Date: 2026-10-01
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "properties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("landlord_id", sa.Uuid(), nullable=False),
        sa.Column("nickname", sa.String(length=100), nullable=False),
        sa.Column("address_line_1", sa.String(length=200), nullable=False),
        sa.Column("address_line_2", sa.String(length=200), nullable=True),
        sa.Column("town", sa.String(length=100), nullable=False),
        sa.Column("postcode", sa.String(length=8), nullable=False),
        sa.Column(
            "ownership_percentage",
            sa.Numeric(precision=5, scale=2),
            server_default="100.00",
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "ownership_percentage > 0 AND ownership_percentage <= 100",
            name="ck_properties_ownership_percentage_range",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_properties"),
    )
    op.create_index("ix_properties_landlord_id", "properties", ["landlord_id"])


def downgrade() -> None:
    op.drop_index("ix_properties_landlord_id", table_name="properties")
    op.drop_table("properties")
