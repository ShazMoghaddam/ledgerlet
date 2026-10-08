"""LedgerLet categories -> HMRC's UK property cumulative summary. Pure functions.

Field names follow HMRC's Property Business API (UK property cumulative period
summary). They're kept in the two tables below so that if HMRC's sandbox rejects a
name, the fix is one line. Every field is always sent, zeros included: each
cumulative update replaces the last, so a figure that drops to zero must be sent
as zero, not left out.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from app.core.exceptions import BusinessRuleError
from app.core.money import from_pence
from app.modules.transactions.categories import TransactionCategory as C

INCOME_FIELDS: dict[C, str] = {
    C.RENTAL_INCOME: "periodAmount",
    C.LEASE_PREMIUM: "premiumsOfLeaseGrant",
    C.REVERSE_PREMIUM: "reversePremiums",
    C.OTHER_INCOME: "otherIncome",
}

EXPENSE_FIELDS: dict[C, str] = {
    C.PREMISES_RUNNING_COSTS: "premisesRunningCosts",
    C.REPAIRS_AND_MAINTENANCE: "repairsAndMaintenance",
    C.NON_RESIDENTIAL_FINANCE_COSTS: "financialCosts",
    C.PROFESSIONAL_FEES: "professionalFees",
    C.COST_OF_SERVICES: "costOfServices",
    C.TRAVEL_COSTS: "travelCosts",
    C.OTHER_EXPENSES: "other",
}

# Mortgage interest: reported separately whichever way expenses are sent.
RESIDENTIAL_FINANCE_FIELD = "residentialFinancialCost"
CONSOLIDATED_FIELD = "consolidatedExpenses"

# HMRC allows a single expenses total when property income is below this.
CONSOLIDATED_EXPENSES_LIMIT_PENCE = 90_000_00


def _amount(pence: int) -> Decimal:
    return from_pence(pence)


def build_uk_property_body(
    totals: dict[C, int],
    period_start: date,
    period_end: date,
    *,
    consolidated_expenses: bool = False,
) -> dict[str, Any]:
    """The JSON HMRC expects, with amounts as 2-decimal pounds (Decimal, serialised later)."""
    unmapped = set(totals) - set(INCOME_FIELDS) - set(EXPENSE_FIELDS) - {
        C.RESIDENTIAL_FINANCE_COSTS
    }
    if unmapped:  # a new category without an HMRC home must never be dropped silently
        raise ValueError(f"No HMRC field for {sorted(unmapped)}")

    income_pence = sum(totals.get(c, 0) for c in INCOME_FIELDS)
    if consolidated_expenses and income_pence >= CONSOLIDATED_EXPENSES_LIMIT_PENCE:
        raise BusinessRuleError(
            "Consolidated expenses are only allowed while property income is below £90,000. "
            "Send itemised expenses instead."
        )

    income = {field: _amount(totals.get(c, 0)) for c, field in INCOME_FIELDS.items()}
    if consolidated_expenses:
        expenses = {
            CONSOLIDATED_FIELD: _amount(sum(totals.get(c, 0) for c in EXPENSE_FIELDS)),
        }
    else:
        expenses = {field: _amount(totals.get(c, 0)) for c, field in EXPENSE_FIELDS.items()}
    expenses[RESIDENTIAL_FINANCE_FIELD] = _amount(totals.get(C.RESIDENTIAL_FINANCE_COSTS, 0))

    return {
        "fromDate": period_start.isoformat(),
        "toDate": period_end.isoformat(),
        "ukProperty": {"income": income, "expenses": expenses},
    }


def to_json(body: dict[str, Any]) -> dict[str, Any]:
    """Decimal -> float for JSON. Exact for 2-decimal values well inside float precision."""
    if isinstance(body, dict):
        return {k: to_json(v) for k, v in body.items()}
    if isinstance(body, Decimal):
        return float(body)
    return body
