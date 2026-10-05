"""HTTP for the tax module. Read-only GET endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.security import CurrentLandlordId
from app.modules.tax.dependencies import TaxServiceDep
from app.modules.tax.periods import PeriodBasis
from app.modules.tax.schemas import ObligationsRead, TaxSummary

router = APIRouter(prefix="/tax", tags=["tax"])

TaxYear = Annotated[
    int | None,
    Query(ge=2020, le=2100, description="Start year, e.g. 2026 for 2026-27. Defaults to now."),
]
Basis = Annotated[
    PeriodBasis,
    Query(description="standard (6 Apr to 5 Jul...) or calendar (1 Apr to 30 Jun...)"),
]


@router.get("/obligations", response_model=ObligationsRead)
def get_obligations(
    landlord_id: CurrentLandlordId,  # required: only signed-in landlords see obligations
    service: TaxServiceDep,
    tax_year: TaxYear = None,
    basis: Basis = PeriodBasis.STANDARD,
):
    return service.obligations(tax_year, basis)


@router.get("/summary", response_model=TaxSummary)
def get_summary(
    landlord_id: CurrentLandlordId,
    service: TaxServiceDep,
    quarter: Annotated[int, Query(ge=1, le=4, description="Cumulative from the year start")],
    tax_year: TaxYear = None,
    basis: Basis = PeriodBasis.STANDARD,
):
    return service.summary(landlord_id, quarter, tax_year, basis)
