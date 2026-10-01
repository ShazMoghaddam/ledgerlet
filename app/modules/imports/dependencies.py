"""Per-request wiring: the import service is built from the other modules' services."""

from typing import Annotated

from fastapi import Depends

from app.modules.imports.service import ImportService
from app.modules.properties.dependencies import PropertyServiceDep
from app.modules.transactions.dependencies import TransactionServiceDep


def get_import_service(
    properties: PropertyServiceDep, transactions: TransactionServiceDep
) -> ImportService:
    return ImportService(properties=properties, transactions=transactions)


ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]
