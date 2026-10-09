"""Pure arithmetic for tax figures. Everything is integer pence.

The rounding rule, written down so totals are reproducible:
    1. Total each category per property (exact, in pence).
    2. Apply the owner's share to each of those totals, rounding half up to the penny.
    3. Add the rounded shares across properties.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, Self

from app.core.money import share_of
from app.modules.transactions.categories import TransactionCategory, TransactionKind


class HasCategoryAndAmount(Protocol):
    category: TransactionCategory
    amount_pence: int


def totals_by_category(items: Iterable[HasCategoryAndAmount]) -> dict[TransactionCategory, int]:
    """Every category present, zero where nothing was recorded."""
    totals = dict.fromkeys(TransactionCategory, 0)
    for item in items:
        totals[item.category] += item.amount_pence
    return totals


def apply_share(
    totals: dict[TransactionCategory, int], ownership_percentage: Decimal
) -> dict[TransactionCategory, int]:
    return {cat: share_of(pence, ownership_percentage) for cat, pence in totals.items()}


def add_totals(*all_totals: dict[TransactionCategory, int]) -> dict[TransactionCategory, int]:
    combined = dict.fromkeys(TransactionCategory, 0)
    for totals in all_totals:
        for cat, pence in totals.items():
            combined[cat] += pence
    return combined


@dataclass(frozen=True)
class Headline:
    """The figures a landlord actually looks at, derived from category totals.

    Residential finance costs (mortgage interest) are kept out of expenses and
    out of profit: HMRC relieves them as a basic-rate tax credit instead.
    """

    income: int
    expenses: int
    residential_finance_costs: int
    profit: int

    @classmethod
    def from_totals(cls, totals: dict[TransactionCategory, int]) -> Self:
        income = sum(p for c, p in totals.items() if c.kind is TransactionKind.INCOME)
        finance = totals[TransactionCategory.RESIDENTIAL_FINANCE_COSTS]
        expenses = sum(p for c, p in totals.items() if c.kind is TransactionKind.EXPENSE) - finance
        return cls(
            income=income,
            expenses=expenses,
            residential_finance_costs=finance,
            profit=income - expenses,
        )
