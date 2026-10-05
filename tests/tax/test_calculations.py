from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.tax.calculations import (
    Headline,
    add_totals,
    apply_share,
    share_of,
    totals_by_category,
)
from app.modules.transactions.categories import TransactionCategory as C


@pytest.mark.parametrize(
    ("pence", "percent", "expected"),
    [
        (100, "100", 100),
        (100, "50", 50),
        (101, "50", 51),  # 50.5p rounds half up
        (80101, "50", 40051),
        (10000, "33.33", 3333),
        (1, "0.01", 0),
        (0, "50", 0),
    ],
)
def test_share_of(pence: int, percent: str, expected: int) -> None:
    assert share_of(pence, Decimal(percent)) == expected


def tx(category: C, pence: int) -> SimpleNamespace:
    return SimpleNamespace(category=category, amount_pence=pence)


def test_totals_include_every_category() -> None:
    totals = totals_by_category([tx(C.RENTAL_INCOME, 100), tx(C.RENTAL_INCOME, 50)])
    assert set(totals) == set(C)
    assert totals[C.RENTAL_INCOME] == 150
    assert totals[C.TRAVEL_COSTS] == 0


def test_share_is_applied_per_category_then_added() -> None:
    a = apply_share(totals_by_category([tx(C.RENTAL_INCOME, 101)]), Decimal("50"))
    b = apply_share(totals_by_category([tx(C.RENTAL_INCOME, 101)]), Decimal("50"))
    assert add_totals(a, b)[C.RENTAL_INCOME] == 102  # 51 + 51, not round(101)


def test_headline_keeps_mortgage_interest_out_of_expenses_and_profit() -> None:
    totals = totals_by_category(
        [
            tx(C.RENTAL_INCOME, 100000),
            tx(C.REPAIRS_AND_MAINTENANCE, 20000),
            tx(C.RESIDENTIAL_FINANCE_COSTS, 30000),
        ]
    )
    h = Headline.from_totals(totals)
    assert (h.income, h.expenses, h.residential_finance_costs, h.profit) == (
        100000,
        20000,
        30000,
        80000,
    )
