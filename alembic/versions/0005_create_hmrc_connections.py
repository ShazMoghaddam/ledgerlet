"""create hmrc connections

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-05

One row per landlord who has authorised LedgerLet at HMRC. Tokens are stored
as Fernet ciphertext (Text), never in the clear.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hmrc_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("landlord_id", sa.Uuid(), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["landlord_id"],
            ["landlords.id"],
            name="fk_hmrc_connections_landlord_id_landlords",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_hmrc_connections"),
        sa.UniqueConstraint("landlord_id", name="uq_hmrc_connections_landlord_id"),
    )


def downgrade() -> None:
    op.drop_table("hmrc_connections")
