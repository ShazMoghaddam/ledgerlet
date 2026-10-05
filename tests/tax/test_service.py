"""A worked example a landlord would recognise, checked to the penny.

Elm Court (owned outright) and Oak Road (owned 50/50), 2026-27, standard periods.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from app.modules.properties.schemas import PropertyCreate
from app.modules.properties.service import PropertyService
from app.modules.tax.periods import ObligationStatus, PeriodBasis
from app.modules.tax.service import TaxService
from app.modules.transactions.categories import TransactionCategory as C
from app.modules.transactions.schemas import TransactionCreate
from app.modules.transactions.service import TransactionService
from tests.properties.fakes import FakePropertyRepository
from tests.transactions.fakes import FakeTransactionRepository

TODAY = date(2026, 10, 10)
STANDARD, CALENDAR = PeriodBasis.STANDARD, PeriodBasis.CALENDAR


@pytest.fixture
def properties() -> PropertyService:
    return PropertyService(FakePropertyRepository())


@pytest.fixture
def transactions(properties) -> TransactionService:
    return TransactionService(
        FakeTransactionRepository(), properties=properties, today=lambda: TODAY
    )


@pytest.fixture
def service(properties, transactions) -> TaxService:
    return TaxService(properties, transactions, today=lambda: TODAY)


def add_property(properties, landlord_id, nickname, line1, share="100") -> UUID:
    return properties.create_property(
        landlord_id,
        PropertyCreate(
            nickname=nickname,
            address_line_1=line1,
            town="London",
            postcode="E1 6AN",
            ownership_percentage=Decimal(share),
        ),
    ).id


def record(transactions, landlord_id, property_id, day, category, amount) -> None:
    transactions.record_transaction(
        landlord_id,
        property_id,
        TransactionCreate(
            transaction_date=day, category=category, description="x", amount=Decimal(amount)
        ),
    )


@pytest.fixture
def portfolio(properties, transactions, landlord_id) -> dict[str, UUID]:
    elm = add_property(properties, landlord_id, "Elm Court", "2 Elm Court")
    oak = add_property(properties, landlord_id, "Oak Road", "9 Oak Road", share="50")

    # Q1 (6 Apr to 5 Jul)
    record(transactions, landlord_id, elm, date(2026, 5, 1), C.RENTAL_INCOME, "1000.00")
    record(transactions, landlord_id, elm, date(2026, 6, 1), C.REPAIRS_AND_MAINTENANCE, "200.00")
    record(transactions, landlord_id, elm, date(2026, 6, 15), C.RESIDENTIAL_FINANCE_COSTS, "300")
    record(transactions, landlord_id, oak, date(2026, 5, 10), C.RENTAL_INCOME, "801.01")
    record(transactions, landlord_id, elm, date(2026, 7, 5), C.TRAVEL_COSTS, "10.00")  # last day
    # Q2 (to 5 Oct)
    record(transactions, landlord_id, elm, date(2026, 7, 6), C.TRAVEL_COSTS, "5.00")  # first day
    record(transactions, landlord_id, elm, date(2026, 8, 1), C.RENTAL_INCOME, "1000.00")
    record(transactions, landlord_id, oak, date(2026, 8, 15), C.PROFESSIONAL_FEES, "120.00")
    # Previous tax year: must never appear
    record(transactions, landlord_id, elm, date(2026, 4, 5), C.RENTAL_INCOME, "999.00")
    return {"elm": elm, "oak": oak}


def amounts(summary) -> dict[C, Decimal]:
    return {c.category: c.amount for c in summary.categories}


def test_q1_totals_at_owners_share(service, portfolio, landlord_id) -> None:
    s = service.summary(landlord_id, 1, 2026, STANDARD)
    # Rent: 1000.00 + 50% of 801.01 (400.505, rounds half up to 400.51)
    assert s.totals.income == Decimal("1400.51")
    assert s.totals.expenses == Decimal("210.00")  # repairs 200 + travel on 5 Jul 10
    assert s.totals.residential_finance_costs == Decimal("300.00")
    assert s.totals.profit == Decimal("1190.51")
    assert amounts(s)[C.TRAVEL_COSTS] == Decimal("10.00")


def test_q2_is_cumulative(service, portfolio, landlord_id) -> None:
    s = service.summary(landlord_id, 2, 2026, STANDARD)
    assert s.totals.income == Decimal("2400.51")
    # repairs 200 + travel 15 + 50% of agent fee 120
    assert s.totals.expenses == Decimal("275.00")
    assert s.totals.profit == Decimal("2125.51")
    assert (s.period_start, s.period_end, s.deadline) == (
        date(2026, 4, 6),
        date(2026, 10, 5),
        date(2026, 11, 7),
    )


def test_every_category_listed_even_when_zero(service, portfolio, landlord_id) -> None:
    s = service.summary(landlord_id, 1, 2026, STANDARD)
    assert len(s.categories) == 12
    assert amounts(s)[C.LEASE_PREMIUM] == Decimal("0.00")


def test_per_property_breakdown(service, portfolio, landlord_id) -> None:
    s = service.summary(landlord_id, 1, 2026, STANDARD)
    by_name = {p.nickname: p for p in s.properties}
    assert by_name["Elm Court"].totals.income == Decimal("1000.00")
    assert by_name["Elm Court"].transaction_count == 4
    assert by_name["Oak Road"].totals.income == Decimal("400.51")
    assert by_name["Oak Road"].ownership_percentage == Decimal("50")


def test_archived_property_still_counts_for_its_period(
    service, properties, portfolio, landlord_id
) -> None:
    properties.archive_property(landlord_id, portfolio["oak"])
    s = service.summary(landlord_id, 1, 2026, STANDARD)
    assert s.totals.income == Decimal("1400.51")
    assert any(p.is_archived for p in s.properties)


def test_other_landlords_data_never_appears(
    service, properties, transactions, portfolio, other_landlord_id
) -> None:
    theirs = add_property(properties, other_landlord_id, "Theirs", "1 High St")
    record(transactions, other_landlord_id, theirs, date(2026, 5, 1), C.RENTAL_INCOME, "50")
    s = service.summary(other_landlord_id, 1, 2026, STANDARD)
    assert s.totals.income == Decimal("50.00")
    assert [p.nickname for p in s.properties] == ["Theirs"]


def test_calendar_basis_uses_calendar_dates(service, properties, transactions, landlord_id) -> None:
    pid = add_property(properties, landlord_id, "Elm Court", "2 Elm Court")
    record(transactions, landlord_id, pid, date(2026, 4, 3), C.RENTAL_INCOME, "100")  # 1-5 April
    record(transactions, landlord_id, pid, date(2026, 7, 3), C.RENTAL_INCOME, "200")  # after 30 Jun

    calendar_q1 = service.summary(landlord_id, 1, 2026, CALENDAR)
    standard_q1 = service.summary(landlord_id, 1, 2026, STANDARD)
    assert calendar_q1.totals.income == Decimal("100.00")
    assert standard_q1.totals.income == Decimal("200.00")


def test_empty_portfolio_gives_zeros(service, landlord_id) -> None:
    s = service.summary(landlord_id, 1, 2026, STANDARD)
    assert s.totals.income == Decimal("0.00")
    assert s.properties == []


def test_tax_year_defaults_to_today(service, landlord_id) -> None:
    assert service.summary(landlord_id, 1, None, STANDARD).tax_year == 2026
    assert service.obligations(None, STANDARD).tax_year_label == "2026-27"


def test_obligation_statuses_on_10_october(service) -> None:
    statuses = [o.status for o in service.obligations(2026, STANDARD).obligations]
    assert statuses == [
        ObligationStatus.PAST_DEADLINE,  # Q1 deadline was 7 Aug
        ObligationStatus.DUE,  # Q2 ended 5 Oct, due 7 Nov
        ObligationStatus.OPEN,
        ObligationStatus.OPEN,
    ]
