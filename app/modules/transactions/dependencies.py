"""Per-request wiring.

The transaction service gets the properties module's own PropertyService as
its property lookup. FastAPI caches get_db per request, so both services
share one database session and one transaction.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.properties.dependencies import PropertyServiceDep
from app.modules.transactions.repository import TransactionRepository
from app.modules.transactions.service import TransactionService


def get_transaction_service(
    db: Annotated[Session, Depends(get_db)], properties: PropertyServiceDep
) -> TransactionService:
    return TransactionService(TransactionRepository(db), properties=properties)


TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]
