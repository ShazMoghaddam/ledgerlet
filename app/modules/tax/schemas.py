"""Response shapes for the tax module. All money is pounds as Decimal strings."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.modules.tax.periods import ObligationStatus, PeriodBasis
from app.modules.transactions.categories import TransactionCategory, TransactionKind


class ObligationRead(BaseModel):
    quarter: int
    period_start: date
    period_end: date
    deadline: date
    status: ObligationStatus


class ObligationsRead(BaseModel):
    tax_year: int
    tax_year_label: str
    basis: PeriodBasis
    obligations: list[ObligationRead]


class CategoryAmount(BaseModel):
    category: TransactionCategory
    label: str
    kind: TransactionKind
    amount: Decimal


class Totals(BaseModel):
    income: Decimal
    expenses: Decimal  # excludes residential finance costs
    residential_finance_costs: Decimal  # relieved as a tax credit, not deducted
    profit: Decimal  # income minus expenses


class PropertySummary(BaseModel):
    property_id: UUID
    nickname: str
    ownership_percentage: Decimal
    is_archived: bool
    transaction_count: int
    totals: Totals  # this owner's share


class TaxSummary(BaseModel):
    """Year-to-date figures for one cumulative update period, at the owner's share."""

    tax_year: int
    tax_year_label: str
    quarter: int
    basis: PeriodBasis
    period_start: date
    period_end: date
    deadline: date
    status: ObligationStatus
    totals: Totals
    categories: list[CategoryAmount]
    properties: list[PropertySummary]
