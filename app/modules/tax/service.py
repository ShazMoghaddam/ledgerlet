"""Builds the figures for HMRC from what's already recorded.

Read-only: it never writes. It asks the properties module for the landlord's
properties (including archived ones, whose past transactions still count) and
the transactions module for each property's transactions in the period.
"""

from collections.abc import Callable
from datetime import date
from typing import Protocol
from uuid import UUID

from app.core.money import from_pence
from app.core.time import uk_today
from app.modules.properties.models import Property
from app.modules.tax.calculations import Headline, add_totals, apply_share, totals_by_category
from app.modules.tax.periods import (
    PeriodBasis,
    tax_year_containing,
    tax_year_label,
    update_period,
    update_periods,
)
from app.modules.tax.schemas import (
    CategoryAmount,
    ObligationRead,
    ObligationsRead,
    PropertySummary,
    TaxSummary,
    Totals,
)
from app.modules.transactions.categories import TransactionCategory
from app.modules.transactions.models import Transaction


class PropertyDirectory(Protocol):
    def list_properties(
        self, landlord_id: UUID, *, include_archived: bool = False
    ) -> list[Property]: ...


class TransactionLister(Protocol):
    def list_transactions(
        self,
        landlord_id: UUID,
        property_id: UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        category: TransactionCategory | None = None,
    ) -> list[Transaction]: ...


class TaxService:
    def __init__(
        self,
        properties: PropertyDirectory,
        transactions: TransactionLister,
        today: Callable[[], date] = uk_today,
    ) -> None:
        self._properties = properties
        self._transactions = transactions
        self._today = today

    def obligations(self, tax_year: int | None, basis: PeriodBasis) -> ObligationsRead:
        year = self._resolve_year(tax_year)
        today = self._today()
        return ObligationsRead(
            tax_year=year,
            tax_year_label=tax_year_label(year),
            basis=basis,
            obligations=[
                ObligationRead(
                    quarter=p.quarter,
                    period_start=p.start,
                    period_end=p.end,
                    deadline=p.deadline,
                    status=p.status(today),
                )
                for p in update_periods(year, basis)
            ],
        )

    def summary(
        self, landlord_id: UUID, quarter: int, tax_year: int | None, basis: PeriodBasis
    ) -> TaxSummary:
        year = self._resolve_year(tax_year)
        period = update_period(year, quarter, basis)

        property_summaries: list[PropertySummary] = []
        shared_totals: list[dict[TransactionCategory, int]] = []
        for prop in self._properties.list_properties(landlord_id, include_archived=True):
            transactions = self._transactions.list_transactions(
                landlord_id, prop.id, date_from=period.start, date_to=period.end
            )
            if not transactions and prop.is_archived:
                continue  # archived and nothing in this period: irrelevant
            share = apply_share(totals_by_category(transactions), prop.ownership_percentage)
            shared_totals.append(share)
            property_summaries.append(
                PropertySummary(
                    property_id=prop.id,
                    nickname=prop.nickname,
                    ownership_percentage=prop.ownership_percentage,
                    is_archived=prop.is_archived,
                    transaction_count=len(transactions),
                    totals=_totals(Headline.from_totals(share)),
                )
            )

        combined = add_totals(*shared_totals)
        return TaxSummary(
            tax_year=year,
            tax_year_label=tax_year_label(year),
            quarter=quarter,
            basis=basis,
            period_start=period.start,
            period_end=period.end,
            deadline=period.deadline,
            status=period.status(self._today()),
            totals=_totals(Headline.from_totals(combined)),
            categories=[
                CategoryAmount(
                    category=cat, label=cat.label, kind=cat.kind, amount=from_pence(pence)
                )
                for cat, pence in combined.items()
            ],
            properties=property_summaries,
        )

    def _resolve_year(self, tax_year: int | None) -> int:
        return tax_year if tax_year is not None else tax_year_containing(self._today())


def _totals(headline: Headline) -> Totals:
    return Totals(
        income=from_pence(headline.income),
        expenses=from_pence(headline.expenses),
        residential_finance_costs=from_pence(headline.residential_finance_costs),
        profit=from_pence(headline.profit),
    )
