"""Layer 1, the API for transactions.

Creating and listing live under a property (they need one); a single
transaction is addressed directly by its id.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, status

from app.core.security import CurrentLandlordId
from app.modules.transactions.categories import TransactionCategory
from app.modules.transactions.dependencies import TransactionServiceDep
from app.modules.transactions.schemas import (
    CategoryRead,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)

router = APIRouter(tags=["transactions"])


# Declared before /transactions/{transaction_id} so "categories" isn't read as an id.
@router.get("/transactions/categories", response_model=list[CategoryRead])
def list_categories():
    return [CategoryRead(value=c, label=c.label, kind=c.kind) for c in TransactionCategory]


@router.post(
    "/properties/{property_id}/transactions",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def record_transaction(
    property_id: UUID,
    payload: TransactionCreate,
    landlord_id: CurrentLandlordId,
    service: TransactionServiceDep,
):
    return service.record_transaction(landlord_id, property_id, payload)


@router.get("/properties/{property_id}/transactions", response_model=list[TransactionRead])
def list_transactions(
    property_id: UUID,
    landlord_id: CurrentLandlordId,
    service: TransactionServiceDep,
    date_from: date | None = None,
    date_to: date | None = None,
    category: TransactionCategory | None = None,
):
    return service.list_transactions(
        landlord_id, property_id, date_from=date_from, date_to=date_to, category=category
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: UUID, landlord_id: CurrentLandlordId, service: TransactionServiceDep
):
    return service.get_transaction(landlord_id, transaction_id)


@router.patch("/transactions/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdate,
    landlord_id: CurrentLandlordId,
    service: TransactionServiceDep,
):
    return service.update_transaction(landlord_id, transaction_id, payload)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: UUID, landlord_id: CurrentLandlordId, service: TransactionServiceDep
) -> None:
    service.delete_transaction(landlord_id, transaction_id)
