"""Layer 3, the repository: the only SQL for transactions.

Note it never filters by landlord. Ownership is checked once, in the service,
via the properties module; this layer just fetches by property or by id.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.modules.transactions.categories import TransactionCategory
from app.modules.transactions.models import Transaction


@dataclass(frozen=True)
class TransactionCriteria:
    """Filters for searching across properties. Ownership is decided by the caller."""

    property_ids: Collection[UUID]
    date_from: date | None = None
    date_to: date | None = None
    category: TransactionCategory | None = None
    text: str | None = None  # matches the description, ignoring case
    amount_pence: int | None = None  # when the search text is an amount, also match it


class TransactionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, transaction: Transaction) -> Transaction:
        self._session.add(transaction)
        self._session.flush()
        return transaction

    def get(self, transaction_id: UUID) -> Transaction | None:
        return self._session.get(Transaction, transaction_id)

    def list_for_property(
        self,
        property_id: UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        category: TransactionCategory | None = None,
    ) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.property_id == property_id)
        if date_from is not None:
            stmt = stmt.where(Transaction.transaction_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Transaction.transaction_date <= date_to)
        if category is not None:
            stmt = stmt.where(Transaction.category == category)
        stmt = stmt.order_by(Transaction.transaction_date, Transaction.created_at)
        return list(self._session.scalars(stmt))

    def search(
        self, criteria: TransactionCriteria, *, limit: int, offset: int
    ) -> list[Transaction]:
        """Newest first, the order a landlord reads a statement in."""
        stmt = self._where(select(Transaction), criteria).order_by(
            Transaction.transaction_date.desc(),
            Transaction.created_at.desc(),
            Transaction.id,  # a stable order, so paging never repeats or skips a row
        )
        return list(self._session.scalars(stmt.limit(limit).offset(offset)))

    def count(self, criteria: TransactionCriteria) -> int:
        stmt = self._where(select(func.count()).select_from(Transaction), criteria)
        return self._session.scalar(stmt) or 0

    def sum_by_property_and_category(
        self, criteria: TransactionCriteria
    ) -> dict[tuple[UUID, TransactionCategory], int]:
        stmt = self._where(
            select(
                Transaction.property_id,
                Transaction.category,
                func.sum(Transaction.amount_pence),
            ),
            criteria,
        ).group_by(Transaction.property_id, Transaction.category)
        return {(pid, cat): int(total) for pid, cat, total in self._session.execute(stmt)}

    @staticmethod
    def _where(stmt: Select, c: TransactionCriteria) -> Select:
        stmt = stmt.where(Transaction.property_id.in_(list(c.property_ids)))
        if c.date_from is not None:
            stmt = stmt.where(Transaction.transaction_date >= c.date_from)
        if c.date_to is not None:
            stmt = stmt.where(Transaction.transaction_date <= c.date_to)
        if c.category is not None:
            stmt = stmt.where(Transaction.category == c.category)
        if c.text:
            matches = Transaction.description.icontains(c.text, autoescape=True)
            if c.amount_pence is not None:
                matches = or_(matches, Transaction.amount_pence == c.amount_pence)
            stmt = stmt.where(matches)
        return stmt

    def delete(self, transaction: Transaction) -> None:
        self._session.delete(transaction)
        self._session.flush()

    def commit(self) -> None:
        self._session.commit()
