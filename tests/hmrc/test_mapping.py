"""Our 12 categories -> HMRC's UK property fields. Pure, so every case is pinned."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError
from app.modules.hmrc.mapping import (
    EXPENSE_FIELDS,
    INCOME_FIELDS,
    build_uk_property_body,
    to_json,
)
from app.modules.transactions.categories import TransactionCategory as C

START, END = date(2026, 4, 6), date(2026, 10, 5)


def totals(**pence: int) -> dict[C, int]:
    base = dict.fromkeys(C, 0)
    base.update({C(k): v for k, v in pence.items()})
    return base


def test_every_category_has_exactly_one_hmrc_home() -> None:
    homes = set(INCOME_FIELDS) | set(EXPENSE_FIELDS) | {C.RESIDENTIAL_FINANCE_COSTS}
    assert homes == set(C)
    assert not set(INCOME_FIELDS) & set(EXPENSE_FIELDS)


def test_itemised_body() -> None:
    body = build_uk_property_body(
        totals(
            rental_income=240051,
            repairs_and_maintenance=20000,
            residential_finance_costs=30000,
            other_expenses=1,
        ),
        START,
        END,
    )
    assert (body["fromDate"], body["toDate"]) == ("2026-04-06", "2026-10-05")
    income = body["ukProperty"]["income"]
    expenses = body["ukProperty"]["expenses"]
    assert income["periodAmount"] == Decimal("2400.51")
    assert income["premiumsOfLeaseGrant"] == Decimal("0.00")  # zeros are always sent
    assert expenses["repairsAndMaintenance"] == Decimal("200.00")
    assert expenses["other"] == Decimal("0.01")
    assert expenses["residentialFinancialCost"] == Decimal("300.00")
    assert "consolidatedExpenses" not in expenses


def test_consolidated_body_keeps_mortgage_interest_separate() -> None:
    body = build_uk_property_body(
        totals(
            rental_income=100000,
            repairs_and_maintenance=20000,
            travel_costs=1550,
            residential_finance_costs=30000,
        ),
        START,
        END,
        consolidated_expenses=True,
    )
    assert body["ukProperty"]["expenses"] == {
        "consolidatedExpenses": Decimal("215.50"),
        "residentialFinancialCost": Decimal("300.00"),
    }


def test_consolidated_refused_at_or_above_90k_income() -> None:
    with pytest.raises(BusinessRuleError, match="90,000"):
        build_uk_property_body(
            totals(rental_income=90_000_00), START, END, consolidated_expenses=True
        )
    build_uk_property_body(totals(rental_income=89_999_99), START, END, consolidated_expenses=True)


def test_to_json_gives_plain_numbers() -> None:
    body = to_json(build_uk_property_body(totals(rental_income=85050), START, END))
    assert body["ukProperty"]["income"]["periodAmount"] == 850.5
    assert isinstance(body["ukProperty"]["income"]["periodAmount"], float)
