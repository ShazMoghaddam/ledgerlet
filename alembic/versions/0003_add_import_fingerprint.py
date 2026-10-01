"""add import fingerprint to transactions

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-01

Nullable, so existing manual transactions are untouched. The unique
constraint means the same bank row can't land in a property twice.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transactions", sa.Column("import_fingerprint", sa.String(length=64), nullable=True)
    )
    op.create_unique_constraint(
        "uq_transactions_property_id_import_fingerprint",
        "transactions",
        ["property_id", "import_fingerprint"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_transactions_property_id_import_fingerprint", "transactions", type_="unique"
    )
    op.drop_column("transactions", "import_fingerprint")
