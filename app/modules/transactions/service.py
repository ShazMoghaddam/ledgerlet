"""Layer 2, the service: rules for recording and changing transactions.

Two collaborators, both injected as Protocols:
- a transaction repository (storage)
- a property lookup (the properties module's public service), used to
  confirm the landlord owns the property. This is the only way the
  transactions module learns anything about properties.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Protocol
from uuid import UUID

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.money import share_of, to_pence
from app.core.time import uk_today
from app.modules.properties.models import Property
from app.modules.transactions.categories import (
    TransactionCategory,
    TransactionKind,
    TransactionSource,
)
from app.modules.transactions.models import Transaction
from app.modules.transactions.repository import TransactionCriteria
from app.modules.transactions.schemas import TransactionCreate, TransactionUpdate


class PropertyLookup(Protocol):
    def get_property(self, landlord_id: UUID, property_id: UUID) -> Property: ...
    def list_properties(
        self, landlord_id: UUID, *, include_archived: bool = False
    ) -> list[Property]: ...


@dataclass(frozen=True)
class TransactionFilters:
    """What a landlord can filter the cross-property list by."""

    property_id: UUID | None = None
    date_from: date | None = None
    date_to: date | None = None
    category: TransactionCategory | None = None
    search: str | None = None


@dataclass(frozen=True)
class SearchResult:
    """A page of rows, plus figures for every matching row (all at the landlord's share)."""

    rows: list[tuple[Transaction, int]]  # each transaction with its share, in pence
    total: int
    money_in_pence: int
    money_out_pence: int


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
    def search(
        self, criteria: TransactionCriteria, *, limit: int, offset: int
    ) -> list[Transaction]: ...
    def count(self, criteria: TransactionCriteria) -> int: ...
    def sum_by_property_and_category(
        self, criteria: TransactionCriteria
    ) -> dict[tuple[UUID, TransactionCategory], int]: ...
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

    def search_transactions(
        self, landlord_id: UUID, filters: TransactionFilters, *, limit: int, offset: int
    ) -> SearchResult:
        """Every property's transactions in one list, archived properties included.

        Totals apply the share per property per category and round there, the
        same rule the tax module uses, so they agree with the tax figures.
        """
        if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
            raise BusinessRuleError("date_from must be on or before date_to")
        if filters.property_id is not None:
            properties = [self._properties.get_property(landlord_id, filters.property_id)]
        else:
            properties = self._properties.list_properties(landlord_id, include_archived=True)
        if not properties:
            return SearchResult(rows=[], total=0, money_in_pence=0, money_out_pence=0)

        shares = {p.id: p.ownership_percentage for p in properties}
        text = (filters.search or "").strip() or None
        criteria = TransactionCriteria(
            property_ids=list(shares),
            date_from=filters.date_from,
            date_to=filters.date_to,
            category=filters.category,
            text=text,
            amount_pence=_amount_in(text),
        )

        money_in = money_out = 0
        for (property_id, category), pence in self._repo.sum_by_property_and_category(
            criteria
        ).items():
            share = share_of(pence, shares[property_id])
            if category.kind is TransactionKind.INCOME:
                money_in += share
            else:
                money_out += share

        page = self._repo.search(criteria, limit=limit, offset=offset)
        return SearchResult(
            rows=[(t, share_of(t.amount_pence, shares[t.property_id])) for t in page],
            total=self._repo.count(criteria),
            money_in_pence=money_in,
            money_out_pence=money_out,
        )

    # Commands

    def record_transaction(
        self,
        landlord_id: UUID,
        property_id: UUID,
        data: TransactionCreate,
        source: TransactionSource = TransactionSource.MANUAL,
    ) -> Transaction:
        prop = self._writable_property(landlord_id, property_id)
        self._ensure_not_future(data.transaction_date)
        transaction = self._repo.add(self._build(prop.id, data, source))
        self._repo.commit()
        return transaction

    def record_imported_transactions(
        self,
        landlord_id: UUID,
        property_id: UUID,
        items: Sequence[tuple[TransactionCreate, str]],
        source: TransactionSource = TransactionSource.CSV_IMPORT,
    ) -> list[Transaction]:
        """All-or-nothing: every row is checked before any is added, then one commit."""
        prop = self._writable_property(landlord_id, property_id)
        for data, _ in items:
            self._ensure_not_future(data.transaction_date)
        created = [self._repo.add(self._build(prop.id, data, source, fp)) for data, fp in items]
        self._repo.commit()
        return created

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

    # Rules and helpers

    def _writable_property(self, landlord_id: UUID, property_id: UUID) -> Property:
        prop = self._properties.get_property(landlord_id, property_id)
        if prop.is_archived:
            raise ConflictError("Can't add transactions to an archived property. Restore it first.")
        return prop

    @staticmethod
    def _build(
        property_id: UUID,
        data: TransactionCreate,
        source: TransactionSource,
        import_fingerprint: str | None = None,
    ) -> Transaction:
        return Transaction(
            property_id=property_id,
            transaction_date=data.transaction_date,
            category=data.category,
            description=data.description,
            amount_pence=to_pence(data.amount),
            source=source,
            import_fingerprint=import_fingerprint,
        )

    def _ensure_not_future(self, transaction_date: date) -> None:
        if transaction_date > self._today():
            raise BusinessRuleError("Transactions can't be dated in the future")

    @staticmethod
    def _ensure_editable(transaction: Transaction) -> None:
        if transaction.is_locked:
            raise ConflictError(
                "This transaction is in a tax year already finalised with HMRC and can't be "
                "changed. Record a correcting transaction instead."
            )


MAX_AMOUNT = Decimal("10000000000")  # the largest amount the API accepts is just under this


def _amount_in(text: str | None) -> int | None:
    """ "96", "96.00", "£1,200" and the like are also searched as amounts, in pence."""
    if not text:
        return None
    cleaned = text.replace("£", "").replace(",", "").strip()
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    if not amount.is_finite() or amount.as_tuple().exponent < -2:
        return None
    if not 0 < amount < MAX_AMOUNT:  # also keeps huge numbers out of the SQL
        return None
    return to_pence(amount)
