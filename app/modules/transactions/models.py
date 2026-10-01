"""Layer 4, the data model: one row per money movement on a property."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.core.money import from_pence
from app.core.types import StrEnumType, sql_in_list
from app.modules.transactions.categories import (
    TransactionCategory,
    TransactionKind,
    TransactionSource,
)


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # Direction comes from the category, so amounts are always positive.
        CheckConstraint("amount_pence > 0", name="amount_positive"),
        CheckConstraint(f"category IN ({sql_in_list(TransactionCategory)})", name="category_valid"),
        CheckConstraint(f"source IN ({sql_in_list(TransactionSource)})", name="source_valid"),
        # The hot query: "this property's transactions between these dates".
        Index("ix_transactions_property_id_transaction_date", "property_id", "transaction_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # RESTRICT: the database refuses to delete a property that has transactions.
    # (Properties are archived, never deleted, but this guarantees it.)
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False
    )

    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[TransactionCategory] = mapped_column(
        StrEnumType(TransactionCategory, length=40), nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    # Full amount as it hit the bank, in pence. A joint owner's share is
    # applied later by the tax module, using the property's ownership_percentage.
    amount_pence: Mapped[int] = mapped_column(BigInteger, nullable=False)

    source: Mapped[TransactionSource] = mapped_column(
        StrEnumType(TransactionSource, length=20),
        nullable=False,
        default=TransactionSource.MANUAL,
    )

    # Set when the quarter containing this transaction is submitted to HMRC.
    # Locked transactions can't be edited or deleted; corrections become new entries.
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def amount(self) -> Decimal:
        return from_pence(self.amount_pence)

    @property
    def kind(self) -> TransactionKind:
        return self.category.kind

    @property
    def is_locked(self) -> bool:
        return self.locked_at is not None

    def __repr__(self) -> str:
        return f"<Transaction {self.id} {self.category} {self.amount_pence}p>"
