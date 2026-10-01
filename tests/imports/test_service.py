"""The import workflow with no database: real services over fake repositories."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.modules.imports.parser import CsvFormatError, Direction
from app.modules.imports.schemas import CsvMapping, ImportRowConfirm, RowStatus
from app.modules.imports.service import ImportService
from app.modules.properties.schemas import PropertyCreate
from app.modules.properties.service import PropertyService
from app.modules.transactions.categories import TransactionCategory, TransactionSource
from app.modules.transactions.schemas import TransactionCreate
from app.modules.transactions.service import TransactionService
from tests.properties.fakes import FakePropertyRepository
from tests.transactions.fakes import FakeTransactionRepository

TODAY = date(2026, 10, 1)
MAPPING = CsvMapping(date_column="Date", description_column="Description", amount_column="Amount")
STATEMENT = (
    b"Date,Description,Amount\n"
    b"01/09/2026,J SMITH RENT,850.00\n"
    b"03/09/2026,BRITISH GAS,-62.40\n"
    b"05/09/2026,BAD ROW,abc\n"
)


@pytest.fixture
def properties() -> PropertyService:
    return PropertyService(FakePropertyRepository())


@pytest.fixture
def tx_repo() -> FakeTransactionRepository:
    return FakeTransactionRepository()


@pytest.fixture
def transactions(tx_repo, properties) -> TransactionService:
    return TransactionService(tx_repo, properties=properties, today=lambda: TODAY)


@pytest.fixture
def service(properties, transactions) -> ImportService:
    return ImportService(properties, transactions, today=lambda: TODAY, max_rows=50)


@pytest.fixture
def property_id(properties: PropertyService, landlord_id: UUID) -> UUID:
    return properties.create_property(
        landlord_id,
        PropertyCreate(
            nickname="Elm", address_line_1="2 Elm Court", town="London", postcode="E1 6AN"
        ),
    ).id


def confirm_rows(preview, categories: dict[str, TransactionCategory]) -> list[ImportRowConfirm]:
    """Turn the valid preview rows into confirm rows, categorised by description."""
    return [
        ImportRowConfirm(
            fingerprint=r.fingerprint,
            transaction_date=r.transaction_date,
            description=r.description,
            amount=r.amount,
            direction=r.direction,
            category=categories[r.description],
        )
        for r in preview.rows
        if r.fingerprint is not None
    ]


CATEGORIES = {
    "J SMITH RENT": TransactionCategory.RENTAL_INCOME,
    "BRITISH GAS": TransactionCategory.PREMISES_RUNNING_COSTS,
}


def test_preview_flags_rows_and_saves_nothing(service, tx_repo, landlord_id, property_id) -> None:
    preview = service.preview(landlord_id, property_id, STATEMENT, MAPPING)
    assert (preview.total, preview.new, preview.invalid) == (3, 2, 1)
    assert preview.rows[0].amount == Decimal("850.00")
    assert preview.rows[1].direction is Direction.OUT
    assert preview.rows[2].status is RowStatus.INVALID
    assert preview.rows[2].fingerprint is None
    assert tx_repo.items == {}


def test_confirm_creates_csv_import_transactions(
    service, tx_repo, landlord_id, property_id
) -> None:
    preview = service.preview(landlord_id, property_id, STATEMENT, MAPPING)
    result = service.confirm(landlord_id, property_id, confirm_rows(preview, CATEGORIES))

    assert (result.created, result.skipped_already_imported) == (2, 0)
    saved = list(tx_repo.items.values())
    assert {t.source for t in saved} == {TransactionSource.CSV_IMPORT}
    assert all(t.import_fingerprint for t in saved)
    assert {t.amount_pence for t in saved} == {85000, 6240}


def test_reimporting_the_same_file_is_detected_and_skipped(
    service, landlord_id, property_id
) -> None:
    first = service.preview(landlord_id, property_id, STATEMENT, MAPPING)
    service.confirm(landlord_id, property_id, confirm_rows(first, CATEGORIES))

    second = service.preview(landlord_id, property_id, STATEMENT, MAPPING)
    assert second.already_imported == 2
    assert second.new == 0

    result = service.confirm(landlord_id, property_id, confirm_rows(second, CATEGORIES))
    assert (result.created, result.skipped_already_imported) == (0, 2)


def test_manual_entry_with_same_date_and_amount_is_a_possible_duplicate(
    service, transactions, landlord_id, property_id
) -> None:
    transactions.record_transaction(
        landlord_id,
        property_id,
        TransactionCreate(
            transaction_date=date(2026, 9, 1),
            category=TransactionCategory.RENTAL_INCOME,
            description="Rent from J Smith",
            amount=Decimal("850"),
        ),
    )
    preview = service.preview(landlord_id, property_id, STATEMENT, MAPPING)
    assert preview.rows[0].status is RowStatus.POSSIBLE_DUPLICATE
    assert preview.rows[1].status is RowStatus.NEW


def test_future_dated_rows_are_invalid(service, landlord_id, property_id) -> None:
    csv = b"Date,Description,Amount\n02/10/2026,TOMORROW,10\n"
    preview = service.preview(landlord_id, property_id, csv, MAPPING)
    assert preview.rows[0].status is RowStatus.INVALID
    assert "future" in (preview.rows[0].message or "")


def test_category_must_match_direction_and_nothing_is_saved(
    service, tx_repo, landlord_id, property_id
) -> None:
    preview = service.preview(landlord_id, property_id, STATEMENT, MAPPING)
    wrong = {**CATEGORIES, "BRITISH GAS": TransactionCategory.OTHER_INCOME}
    with pytest.raises(BusinessRuleError, match="Row 2"):
        service.confirm(landlord_id, property_id, confirm_rows(preview, wrong))
    assert tx_repo.items == {}


def test_same_row_sent_twice_in_one_confirm_is_saved_once(
    service, tx_repo, landlord_id, property_id
) -> None:
    preview = service.preview(landlord_id, property_id, STATEMENT, MAPPING)
    rows = confirm_rows(preview, CATEGORIES)
    result = service.confirm(landlord_id, property_id, rows + rows[:1])
    assert (result.created, result.skipped_already_imported) == (2, 1)
    assert len(tx_repo.items) == 2


def test_archived_property_cannot_import(service, properties, landlord_id, property_id) -> None:
    properties.archive_property(landlord_id, property_id)
    with pytest.raises(ConflictError):
        service.preview(landlord_id, property_id, STATEMENT, MAPPING)


def test_other_landlords_property_is_not_found(service, other_landlord_id, property_id) -> None:
    with pytest.raises(NotFoundError):
        service.preview(other_landlord_id, property_id, STATEMENT, MAPPING)


def test_unknown_property_is_not_found(service, landlord_id) -> None:
    with pytest.raises(NotFoundError):
        service.preview(landlord_id, uuid4(), STATEMENT, MAPPING)


def test_row_limit(service, landlord_id, property_id) -> None:
    lines = ["Date,Description,Amount"] + [f"01/09/2026,ROW {i},1" for i in range(51)]
    with pytest.raises(CsvFormatError, match="limit"):
        service.preview(landlord_id, property_id, "\n".join(lines).encode(), MAPPING)


def test_file_with_only_a_header_is_rejected(service, landlord_id, property_id) -> None:
    with pytest.raises(CsvFormatError):
        service.preview(landlord_id, property_id, b"Date,Description,Amount\n", MAPPING)
