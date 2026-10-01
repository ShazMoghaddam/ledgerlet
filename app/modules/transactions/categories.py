"""Transaction categories, aligned to HMRC's MTD UK property update headings.

Keeping LedgerLet's categories one-to-one with HMRC's means the quarterly
submission is a straight sum per category, with no translation step.
"""

from enum import StrEnum


class TransactionKind(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class TransactionCategory(StrEnum):
    # Income
    RENTAL_INCOME = "rental_income"
    LEASE_PREMIUM = "lease_premium"
    REVERSE_PREMIUM = "reverse_premium"
    OTHER_INCOME = "other_income"

    # Expenses
    PREMISES_RUNNING_COSTS = "premises_running_costs"
    REPAIRS_AND_MAINTENANCE = "repairs_and_maintenance"
    NON_RESIDENTIAL_FINANCE_COSTS = "non_residential_finance_costs"
    PROFESSIONAL_FEES = "professional_fees"
    COST_OF_SERVICES = "cost_of_services"
    TRAVEL_COSTS = "travel_costs"
    OTHER_EXPENSES = "other_expenses"

    # Mortgage interest on residential lets. NOT deducted like other expenses:
    # HMRC requires it reported separately and it earns a basic-rate tax credit.
    RESIDENTIAL_FINANCE_COSTS = "residential_finance_costs"

    @property
    def kind(self) -> TransactionKind:
        return TransactionKind.INCOME if self in INCOME_CATEGORIES else TransactionKind.EXPENSE

    @property
    def label(self) -> str:
        return LABELS[self]


INCOME_CATEGORIES: frozenset[TransactionCategory] = frozenset(
    {
        TransactionCategory.RENTAL_INCOME,
        TransactionCategory.LEASE_PREMIUM,
        TransactionCategory.REVERSE_PREMIUM,
        TransactionCategory.OTHER_INCOME,
    }
)

LABELS: dict[TransactionCategory, str] = {
    TransactionCategory.RENTAL_INCOME: "Rental income",
    TransactionCategory.LEASE_PREMIUM: "Premiums for the grant of a lease",
    TransactionCategory.REVERSE_PREMIUM: "Reverse premiums and inducements",
    TransactionCategory.OTHER_INCOME: "Other property income",
    TransactionCategory.PREMISES_RUNNING_COSTS: "Rent, rates, insurance and ground rent",
    TransactionCategory.REPAIRS_AND_MAINTENANCE: "Repairs and maintenance",
    TransactionCategory.NON_RESIDENTIAL_FINANCE_COSTS: "Non-residential property finance costs",
    TransactionCategory.PROFESSIONAL_FEES: "Legal, management and other professional fees",
    TransactionCategory.COST_OF_SERVICES: "Cost of services provided, including wages",
    TransactionCategory.TRAVEL_COSTS: "Travel costs",
    TransactionCategory.OTHER_EXPENSES: "Other allowable property expenses",
    TransactionCategory.RESIDENTIAL_FINANCE_COSTS: "Residential property finance costs",
}


class TransactionSource(StrEnum):
    """Where a transaction came from. Each source is a separate way in."""

    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    OPEN_BANKING = "open_banking"
