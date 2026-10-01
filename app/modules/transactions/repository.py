"""Layer 3, the repository: the only SQL for transactions.

Note it never filters by landlord. Ownership is checked once, in the service,
via the properties module; this layer just fetches by property or by id.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.transactions.categories import TransactionCategory
from app.modules.transactions.models import Transaction


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

    def delete(self, transaction: Transaction) -> None:
        self._session.delete(transaction)
        self._session.flush()

    def commit(self) -> None:
        self._session.commit()
