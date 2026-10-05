"""create landlords and link properties to them

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-05

Includes a data migration. Properties created before real sign-in used the
X-Landlord-Id header, so their landlord ids have no row yet. Each gets a
placeholder landlord (issuer "legacy-header") so the new foreign key can be
added without losing anything.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "landlords",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("auth_issuer", sa.String(length=255), nullable=False),
        sa.Column("auth_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column(
            "period_basis", sa.String(length=20), server_default="standard", nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "period_basis IN ('standard', 'calendar')", name="ck_landlords_period_basis_valid"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_landlords"),
        sa.UniqueConstraint(
            "auth_issuer", "auth_subject", name="uq_landlords_auth_issuer_auth_subject"
        ),
    )

    op.execute(
        """
        INSERT INTO landlords (id, auth_issuer, auth_subject, period_basis, created_at, updated_at)
        SELECT DISTINCT landlord_id, 'legacy-header', CAST(landlord_id AS VARCHAR(255)),
               'standard', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM properties
        """
    )

    op.create_foreign_key(
        "fk_properties_landlord_id_landlords",
        "properties",
        "landlords",
        ["landlord_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_properties_landlord_id_landlords", "properties", type_="foreignkey")
    op.drop_table("landlords")
