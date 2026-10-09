"""The cross-property list: filters, paging, ownership and totals at the landlord's share."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.properties.schemas import PropertyCreate
from app.modules.properties.service import PropertyService
from app.modules.transactions.categories import TransactionCategory as Cat
from app.modules.transactions.schemas import TransactionCreate
from app.modules.transactions.service import TransactionFilters, TransactionService, _amount_in
from tests.properties.fakes import FakePropertyRepository
from tests.transactions.fakes import FakeTransactionRepository

TODAY = date(2026, 10, 9)


@pytest.fixture
def properties() -> PropertyService:
    return PropertyService(FakePropertyRepository())


@pytest.fixture
def service(properties) -> TransactionService:
    return TransactionService(FakeTransactionRepository(), properties, today=lambda: TODAY)


def add_property(properties, landlord_id, nickname, share="100.00") -> UUID:
    return properties.create_property(
        landlord_id,
        PropertyCreate(
            nickname=nickname,
            address_line_1=f"1 {nickname}",
            town="London",
            postcode="SW1A 1AA",
            ownership_percentage=Decimal(share),
        ),
    ).id


def record(service, landlord_id, property_id, day, category, description, amount):
    service.record_transaction(
        landlord_id,
        property_id,
        TransactionCreate(
            transaction_date=day,
            category=category,
            description=description,
            amount=Decimal(amount),
        ),
    )


@pytest.fixture
def portfolio(service, properties, landlord_id):
    """Elm Court owned outright, Oak Road half owned (the design's sample data, abridged)."""
    elm = add_property(properties, landlord_id, "Elm Court")
    oak = add_property(properties, landlord_id, "Oak Road", "50.00")
    record(service, landlord_id, elm, date(2026, 10, 2), Cat.RENTAL_INCOME, "October rent", "1200")
    record(service, landlord_id, oak, date(2026, 10, 1), Cat.RENTAL_INCOME, "October rent", "1600")
    record(
        service,
        landlord_id,
        elm,
        date(2026, 10, 1),
        Cat.RESIDENTIAL_FINANCE_COSTS,
        "Mortgage interest",
        "490",
    )
    record(
        service,
        landlord_id,
        oak,
        date(2026, 10, 3),
        Cat.REPAIRS_AND_MAINTENANCE,
        "Boiler service",
        "96",
    )
    return elm, oak


def search(service, landlord_id, limit=50, offset=0, **filters):
    return service.search_transactions(
        landlord_id, TransactionFilters(**filters), limit=limit, offset=offset
    )


def test_lists_every_property_newest_first(service, landlord_id, portfolio) -> None:
    result = search(service, landlord_id)
    assert [t.description for t, _ in result.rows][0] == "Boiler service"
    assert [t.transaction_date for t, _ in result.rows] == sorted(
        (t.transaction_date for t, _ in result.rows), reverse=True
    )
    assert result.total == 4


def test_each_row_carries_the_landlords_share(service, landlord_id, portfolio) -> None:
    shares = {t.description: p for t, p in search(service, landlord_id, search="boiler").rows}
    assert shares == {"Boiler service": 4800}


def test_totals_are_at_share_and_count_mortgage_interest_as_money_out(
    service, landlord_id, portfolio
) -> None:
    result = search(service, landlord_id)
    assert result.money_in_pence == 120000 + 80000
    assert result.money_out_pence == 49000 + 4800


def test_totals_cover_every_match_not_just_the_page(service, landlord_id, portfolio) -> None:
    result = search(service, landlord_id, limit=1)
    assert len(result.rows) == 1
    assert result.total == 4
    assert result.money_in_pence == 200000


def test_paging_walks_through_without_repeats(service, landlord_id, portfolio) -> None:
    seen = [t.id for offset in range(4) for t, _ in search(service, landlord_id, 1, offset).rows]
    assert len(set(seen)) == 4


def test_filter_by_property(service, landlord_id, portfolio) -> None:
    _, oak = portfolio
    result = search(service, landlord_id, property_id=oak)
    assert {t.property_id for t, _ in result.rows} == {oak}
    assert (result.money_in_pence, result.money_out_pence) == (80000, 4800)


def test_filter_by_dates_and_category(service, landlord_id, portfolio) -> None:
    result = search(
        service,
        landlord_id,
        date_from=date(2026, 10, 2),
        date_to=date(2026, 10, 9),
        category=Cat.RENTAL_INCOME,
    )
    assert [t.description for t, _ in result.rows] == ["October rent"]


def test_search_matches_an_amount_too(service, landlord_id, portfolio) -> None:
    assert [t.description for t, _ in search(service, landlord_id, search="£96.00").rows] == [
        "Boiler service"
    ]
    assert search(service, landlord_id, search="  ").total == 4  # blank means no search


def test_someone_elses_property_is_not_found(service, landlord_id, portfolio) -> None:
    _, oak = portfolio
    with pytest.raises(NotFoundError):
        search(service, uuid4(), property_id=oak)


def test_another_landlord_sees_nothing(service, portfolio) -> None:
    result = search(service, uuid4())
    assert (result.total, result.money_in_pence, result.rows) == (0, 0, [])


def test_dates_the_wrong_way_round_are_refused(service, landlord_id, portfolio) -> None:
    with pytest.raises(BusinessRuleError):
        search(service, landlord_id, date_from=date(2026, 10, 9), date_to=date(2026, 4, 6))


@pytest.mark.parametrize(
    ("text", "pence"),
    [
        ("96", 9600),
        ("96.5", 9650),
        ("£1,200.00", 120000),
        ("boiler", None),
        ("0", None),
        ("-5", None),
        ("1.005", None),
        ("NaN", None),
        ("99999999999999999999", None),
    ],
)
def test_amount_in_search_text(text: str, pence: int | None) -> None:
    assert _amount_in(text) == pence
