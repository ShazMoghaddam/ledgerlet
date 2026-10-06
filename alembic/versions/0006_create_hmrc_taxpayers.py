"""create hmrc taxpayers

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-06

The landlord's identity at HMRC: National Insurance number (Fernet ciphertext)
and the chosen UK property business id.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hmrc_taxpayers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("landlord_id", sa.Uuid(), nullable=False),
        sa.Column("nino_encrypted", sa.Text(), nullable=False),
        sa.Column("uk_property_business_id", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["landlord_id"],
            ["landlords.id"],
            name="fk_hmrc_taxpayers_landlord_id_landlords",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_hmrc_taxpayers"),
        sa.UniqueConstraint("landlord_id", name="uq_hmrc_taxpayers_landlord_id"),
    )


def downgrade() -> None:
    op.drop_table("hmrc_taxpayers")
