"""In-memory stand-in for TransactionRepository."""

from datetime import date
from uuid import UUID, uuid4

from app.core.time import utc_now
from app.modules.transactions.categories import TransactionCategory
from app.modules.transactions.models import Transaction
from app.modules.transactions.repository import TransactionCriteria


class FakeTransactionRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Transaction] = {}
        self.commit_count = 0

    def add(self, transaction: Transaction) -> Transaction:
        if transaction.id is None:
            transaction.id = uuid4()
        now = utc_now()
        transaction.created_at = transaction.created_at or now
        transaction.updated_at = transaction.updated_at or now
        self.items[transaction.id] = transaction
        return transaction

    def get(self, transaction_id: UUID) -> Transaction | None:
        return self.items.get(transaction_id)

    def list_for_property(
        self,
        property_id: UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        category: TransactionCategory | None = None,
    ) -> list[Transaction]:
        found = [
            t
            for t in self.items.values()
            if t.property_id == property_id
            and (date_from is None or t.transaction_date >= date_from)
            and (date_to is None or t.transaction_date <= date_to)
            and (category is None or t.category == category)
        ]
        return sorted(found, key=lambda t: (t.transaction_date, t.created_at))

    def _matching(self, c: TransactionCriteria) -> list[Transaction]:
        def matches(t: Transaction) -> bool:
            text_ok = not c.text or (
                c.text.lower() in t.description.lower()
                or (c.amount_pence is not None and t.amount_pence == c.amount_pence)
            )
            return (
                t.property_id in c.property_ids
                and (c.date_from is None or t.transaction_date >= c.date_from)
                and (c.date_to is None or t.transaction_date <= c.date_to)
                and (c.category is None or t.category == c.category)
                and text_ok
            )

        return [t for t in self.items.values() if matches(t)]

    def search(
        self, criteria: TransactionCriteria, *, limit: int, offset: int
    ) -> list[Transaction]:
        found = sorted(
            self._matching(criteria),
            key=lambda t: (t.transaction_date, t.created_at),
            reverse=True,
        )
        return found[offset : offset + limit]

    def count(self, criteria: TransactionCriteria) -> int:
        return len(self._matching(criteria))

    def sum_by_property_and_category(
        self, criteria: TransactionCriteria
    ) -> dict[tuple[UUID, TransactionCategory], int]:
        totals: dict[tuple[UUID, TransactionCategory], int] = {}
        for t in self._matching(criteria):
            key = (t.property_id, t.category)
            totals[key] = totals.get(key, 0) + t.amount_pence
        return totals

    def delete(self, transaction: Transaction) -> None:
        del self.items[transaction.id]

    def commit(self) -> None:
        self.commit_count += 1
