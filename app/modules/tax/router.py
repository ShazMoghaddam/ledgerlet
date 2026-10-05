"""HTTP for the tax module. Read-only GET endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.modules.landlords.dependencies import CurrentLandlord
from app.modules.tax.dependencies import TaxServiceDep
from app.modules.tax.periods import PeriodBasis
from app.modules.tax.schemas import ObligationsRead, TaxSummary

router = APIRouter(prefix="/tax", tags=["tax"])

TaxYear = Annotated[
    int | None,
    Query(ge=2020, le=2100, description="Start year, e.g. 2026 for 2026-27. Defaults to now."),
]
Basis = Annotated[
    PeriodBasis | None,
    Query(description="standard or calendar. Defaults to your saved setting (see /me)."),
]


@router.get("/obligations", response_model=ObligationsRead)
def get_obligations(
    landlord: CurrentLandlord,
    service: TaxServiceDep,
    tax_year: TaxYear = None,
    basis: Basis = None,
):
    return service.obligations(tax_year, basis or landlord.period_basis)


@router.get("/summary", response_model=TaxSummary)
def get_summary(
    landlord: CurrentLandlord,
    service: TaxServiceDep,
    quarter: Annotated[int, Query(ge=1, le=4, description="Cumulative from the year start")],
    tax_year: TaxYear = None,
    basis: Basis = None,
):
    return service.summary(landlord.id, quarter, tax_year, basis or landlord.period_basis)
