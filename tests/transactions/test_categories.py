from app.modules.transactions.categories import (
    LABELS,
    TransactionCategory,
    TransactionKind,
)


def test_every_category_has_a_label() -> None:
    assert set(LABELS) == set(TransactionCategory)


def test_income_categories() -> None:
    income = {c for c in TransactionCategory if c.kind is TransactionKind.INCOME}
    assert income == {
        TransactionCategory.RENTAL_INCOME,
        TransactionCategory.LEASE_PREMIUM,
        TransactionCategory.REVERSE_PREMIUM,
        TransactionCategory.OTHER_INCOME,
    }


def test_residential_finance_costs_are_their_own_category() -> None:
    # Mortgage interest must never be lumped in with ordinary finance costs.
    assert TransactionCategory.RESIDENTIAL_FINANCE_COSTS.kind is TransactionKind.EXPENSE
    assert (
        TransactionCategory.RESIDENTIAL_FINANCE_COSTS
        != TransactionCategory.NON_RESIDENTIAL_FINANCE_COSTS
    )


def test_values_are_stable_strings() -> None:
    # Stored in the database: renaming one needs a migration.
    assert TransactionCategory.RENTAL_INCOME == "rental_income"
