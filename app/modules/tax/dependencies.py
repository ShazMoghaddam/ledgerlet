"""Per-request wiring: the tax service reads through the other modules' services."""

from typing import Annotated

from fastapi import Depends

from app.modules.properties.dependencies import PropertyServiceDep
from app.modules.tax.service import TaxService
from app.modules.transactions.dependencies import TransactionServiceDep


def get_tax_service(
    properties: PropertyServiceDep, transactions: TransactionServiceDep
) -> TaxService:
    return TaxService(properties=properties, transactions=transactions)


TaxServiceDep = Annotated[TaxService, Depends(get_tax_service)]
