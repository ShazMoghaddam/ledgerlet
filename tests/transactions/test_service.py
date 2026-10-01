"""Transaction rules with no database: fake repositories behind real services."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.modules.properties.schemas import PropertyCreate
from app.modules.properties.service import PropertyService
from app.modules.transactions.categories import (
    TransactionCategory,
    TransactionKind,
    TransactionSource,
)
from app.modules.transactions.schemas import TransactionCreate, TransactionUpdate
from app.modules.transactions.service import TransactionService
from tests.properties.fakes import FakePropertyRepository
from tests.transactions.fakes import FakeTransactionRepository

TODAY = date(2026, 10, 1)


def tx(**overrides: object) -> TransactionCreate:
    base = {
        "transaction_date": date(2026, 9, 1),
        "category": TransactionCategory.RENTAL_INCOME,
        "description": "September rent",
        "amount": Decimal("850.00"),
    }
    return TransactionCreate(**{**base, **overrides})


@pytest.fixture
def properties() -> PropertyService:
    return PropertyService(FakePropertyRepository())


@pytest.fixture
def repo() -> FakeTransactionRepository:
    return FakeTransactionRepository()


@pytest.fixture
def service(repo, properties) -> TransactionService:
    return TransactionService(repo, properties=properties, today=lambda: TODAY)


@pytest.fixture
def property_id(properties: PropertyService, landlord_id: UUID) -> UUID:
    prop = properties.create_property(
        landlord_id,
        PropertyCreate(
            nickname="Elm Court", address_line_1="2 Elm Court", town="London", postcode="SW1A 1AA"
        ),
    )
    return prop.id


def test_record_stores_pence_and_manual_source(service, landlord_id, property_id) -> None:
    t = service.record_transaction(landlord_id, property_id, tx(amount=Decimal("850.5")))
    assert t.amount_pence == 85050
    assert t.amount == Decimal("850.50")
    assert t.source is TransactionSource.MANUAL
    assert t.kind is TransactionKind.INCOME


def test_record_on_someone_elses_property_is_not_found(
    service, other_landlord_id, property_id
) -> None:
    with pytest.raises(NotFoundError):
        service.record_transaction(other_landlord_id, property_id, tx())


def test_record_on_missing_property_is_not_found(service, landlord_id) -> None:
    with pytest.raises(NotFoundError):
        service.record_transaction(landlord_id, uuid4(), tx())


def test_record_on_archived_property_conflicts(
    service, properties, landlord_id, property_id
) -> None:
    properties.archive_property(landlord_id, property_id)
    with pytest.raises(ConflictError):
        service.record_transaction(landlord_id, property_id, tx())


def test_today_is_allowed_but_tomorrow_is_not(service, landlord_id, property_id) -> None:
    service.record_transaction(landlord_id, property_id, tx(transaction_date=TODAY))
    with pytest.raises(BusinessRuleError):
        service.record_transaction(landlord_id, property_id, tx(transaction_date=date(2026, 10, 2)))


def test_get_someone_elses_transaction_is_not_found(
    service, landlord_id, other_landlord_id, property_id
) -> None:
    t = service.record_transaction(landlord_id, property_id, tx())
    with pytest.raises(NotFoundError):
        service.get_transaction(other_landlord_id, t.id)


def test_update_amount_and_category(service, landlord_id, property_id) -> None:
    t = service.record_transaction(landlord_id, property_id, tx())
    updated = service.update_transaction(
        landlord_id,
        t.id,
        TransactionUpdate(
            amount=Decimal("120"), category=TransactionCategory.REPAIRS_AND_MAINTENANCE
        ),
    )
    assert updated.amount_pence == 12000
    assert updated.kind is TransactionKind.EXPENSE
    assert updated.description == "September rent"


def test_update_to_future_date_is_rejected(service, landlord_id, property_id) -> None:
    t = service.record_transaction(landlord_id, property_id, tx())
    with pytest.raises(BusinessRuleError):
        service.update_transaction(
            landlord_id, t.id, TransactionUpdate(transaction_date=date(2027, 1, 1))
        )


def test_locked_transaction_cannot_be_edited_or_deleted(
    service, landlord_id, property_id
) -> None:
    t = service.record_transaction(landlord_id, property_id, tx())
    t.locked_at = datetime(2026, 9, 30, tzinfo=UTC)
    with pytest.raises(ConflictError):
        service.update_transaction(landlord_id, t.id, TransactionUpdate(description="x"))
    with pytest.raises(ConflictError):
        service.delete_transaction(landlord_id, t.id)


def test_delete_removes(service, repo, landlord_id, property_id) -> None:
    t = service.record_transaction(landlord_id, property_id, tx())
    service.delete_transaction(landlord_id, t.id)
    assert t.id not in repo.items


def test_list_filters_and_orders(service, landlord_id, property_id) -> None:
    service.record_transaction(landlord_id, property_id, tx(transaction_date=date(2026, 9, 1)))
    service.record_transaction(
        landlord_id,
        property_id,
        tx(
            transaction_date=date(2026, 7, 1),
            category=TransactionCategory.REPAIRS_AND_MAINTENANCE,
            description="Boiler",
        ),
    )
    service.record_transaction(landlord_id, property_id, tx(transaction_date=date(2026, 4, 1)))

    dates = [t.transaction_date for t in service.list_transactions(landlord_id, property_id)]
    assert dates == [date(2026, 4, 1), date(2026, 7, 1), date(2026, 9, 1)]

    in_range = service.list_transactions(
        landlord_id, property_id, date_from=date(2026, 6, 1), date_to=date(2026, 8, 31)
    )
    assert [t.description for t in in_range] == ["Boiler"]

    rent = service.list_transactions(
        landlord_id, property_id, category=TransactionCategory.RENTAL_INCOME
    )
    assert len(rent) == 2


def test_list_rejects_inverted_range(service, landlord_id, property_id) -> None:
    with pytest.raises(BusinessRuleError):
        service.list_transactions(
            landlord_id, property_id, date_from=date(2026, 9, 1), date_to=date(2026, 8, 1)
        )


def test_list_someone_elses_property_is_not_found(
    service, other_landlord_id, property_id
) -> None:
    with pytest.raises(NotFoundError):
        service.list_transactions(other_landlord_id, property_id)
