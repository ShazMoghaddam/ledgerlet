"""create transactions table

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01

The allowed category and source values are written out literally here rather
than imported from the app. A migration is a frozen snapshot: if the enums
change later, that change gets its own migration, and this one must still
describe exactly what it created.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORIES = (
    "'rental_income', 'lease_premium', 'reverse_premium', 'other_income', "
    "'premises_running_costs', 'repairs_and_maintenance', 'non_residential_finance_costs', "
    "'professional_fees', 'cost_of_services', 'travel_costs', 'other_expenses', "
    "'residential_finance_costs'"
)
SOURCES = "'manual', 'csv_import', 'open_banking'"


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount_pence", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount_pence > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint(f"category IN ({CATEGORIES})", name="ck_transactions_category_valid"),
        sa.CheckConstraint(f"source IN ({SOURCES})", name="ck_transactions_source_valid"),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name="fk_transactions_property_id_properties",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
    )
    op.create_index(
        "ix_transactions_property_id_transaction_date",
        "transactions",
        ["property_id", "transaction_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_property_id_transaction_date", table_name="transactions")
    op.drop_table("transactions")
