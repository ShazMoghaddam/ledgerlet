"""Layer 2, the service: rules for recording and changing transactions.

Two collaborators, both injected as Protocols:
- a transaction repository (storage)
- a property lookup (the properties module's public service), used to
  confirm the landlord owns the property. This is the only way the
  transactions module learns anything about properties.
"""

from collections.abc import Callable
from datetime import date
from typing import Protocol
from uuid import UUID

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.money import to_pence
from app.core.time import uk_today
from app.modules.properties.models import Property
from app.modules.transactions.categories import TransactionCategory, TransactionSource
from app.modules.transactions.models import Transaction
from app.modules.transactions.schemas import TransactionCreate, TransactionUpdate


class PropertyLookup(Protocol):
    def get_property(self, landlord_id: UUID, property_id: UUID) -> Property: ...


class TransactionRepositoryProtocol(Protocol):
    def add(self, transaction: Transaction) -> Transaction: ...
    def get(self, transaction_id: UUID) -> Transaction | None: ...
    def list_for_property(
        self,
        property_id: UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        category: TransactionCategory | None = None,
    ) -> list[Transaction]: ...
    def delete(self, transaction: Transaction) -> None: ...
    def commit(self) -> None: ...


class TransactionService:
    def __init__(
        self,
        repository: TransactionRepositoryProtocol,
        properties: PropertyLookup,
        today: Callable[[], date] = uk_today,
    ) -> None:
        self._repo = repository
        self._properties = properties
        self._today = today

    # Queries

    def get_transaction(self, landlord_id: UUID, transaction_id: UUID) -> Transaction:
        transaction = self._repo.get(transaction_id)
        if transaction is None:
            raise NotFoundError(f"Transaction {transaction_id} not found")
        try:
            self._properties.get_property(landlord_id, transaction.property_id)
        except NotFoundError:
            # Someone else's transaction: indistinguishable from a missing one.
            raise NotFoundError(f"Transaction {transaction_id} not found") from None
        return transaction

    def list_transactions(
        self,
        landlord_id: UUID,
        property_id: UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        category: TransactionCategory | None = None,
    ) -> list[Transaction]:
        self._properties.get_property(landlord_id, property_id)  # ownership check
        if date_from and date_to and date_from > date_to:
            raise BusinessRuleError("date_from must be on or before date_to")
        return self._repo.list_for_property(
            property_id, date_from=date_from, date_to=date_to, category=category
        )

    # Commands

    def record_transaction(
        self,
        landlord_id: UUID,
        property_id: UUID,
        data: TransactionCreate,
        source: TransactionSource = TransactionSource.MANUAL,
    ) -> Transaction:
        prop = self._properties.get_property(landlord_id, property_id)
        if prop.is_archived:
            raise ConflictError("Can't add transactions to an archived property. Restore it first.")
        self._ensure_not_future(data.transaction_date)

        transaction = Transaction(
            property_id=prop.id,
            transaction_date=data.transaction_date,
            category=data.category,
            description=data.description,
            amount_pence=to_pence(data.amount),
            source=source,
        )
        self._repo.add(transaction)
        self._repo.commit()
        return transaction

    def update_transaction(
        self, landlord_id: UUID, transaction_id: UUID, data: TransactionUpdate
    ) -> Transaction:
        transaction = self.get_transaction(landlord_id, transaction_id)
        self._ensure_editable(transaction)

        changes = data.model_dump(exclude_unset=True)
        if "transaction_date" in changes:
            self._ensure_not_future(changes["transaction_date"])
        if "amount" in changes:
            transaction.amount_pence = to_pence(changes.pop("amount"))
        for field, value in changes.items():
            setattr(transaction, field, value)

        self._repo.commit()
        return transaction

    def delete_transaction(self, landlord_id: UUID, transaction_id: UUID) -> None:
        transaction = self.get_transaction(landlord_id, transaction_id)
        self._ensure_editable(transaction)
        self._repo.delete(transaction)
        self._repo.commit()

    # Rules

    def _ensure_not_future(self, transaction_date: date) -> None:
        if transaction_date > self._today():
            raise BusinessRuleError("Transactions can't be dated in the future")

    @staticmethod
    def _ensure_editable(transaction: Transaction) -> None:
        if transaction.is_locked:
            raise ConflictError(
                "This transaction is in a period already submitted to HMRC and can't be "
                "changed. Record a correcting transaction instead."
            )
