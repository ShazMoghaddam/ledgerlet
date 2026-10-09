"""Layer 1, the API for transactions.

Creating and listing live under a property (they need one); a single
transaction is addressed directly by its id.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.money import from_pence
from app.modules.landlords.dependencies import CurrentLandlordId
from app.modules.transactions.categories import TransactionCategory
from app.modules.transactions.dependencies import TransactionServiceDep
from app.modules.transactions.schemas import (
    CategoryRead,
    TransactionCreate,
    TransactionListItem,
    TransactionPage,
    TransactionRead,
    TransactionUpdate,
)
from app.modules.transactions.service import TransactionFilters

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


@router.get("/transactions", response_model=TransactionPage)
def search_transactions(
    landlord_id: CurrentLandlordId,
    service: TransactionServiceDep,
    property_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    category: TransactionCategory | None = None,
    q: Annotated[str | None, Query(max_length=100, description="Description or amount")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """All of the landlord's transactions across properties, newest first, one page at a time."""
    filters = TransactionFilters(
        property_id=property_id,
        date_from=date_from,
        date_to=date_to,
        category=category,
        search=q,
    )
    result = service.search_transactions(landlord_id, filters, limit=limit, offset=offset)
    return TransactionPage(
        items=[_with_share(t, p) for t, p in result.rows],
        total=result.total,
        limit=limit,
        offset=offset,
        money_in=from_pence(result.money_in_pence),
        money_out=from_pence(result.money_out_pence),
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionListItem)
def get_transaction(
    transaction_id: UUID, landlord_id: CurrentLandlordId, service: TransactionServiceDep
):
    """One transaction, with the landlord's share worked out as the list does."""
    transaction, share = service.get_transaction_with_share(landlord_id, transaction_id)
    return _with_share(transaction, share)


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


def _with_share(transaction, share_pence: int) -> TransactionListItem:
    read = TransactionRead.model_validate(transaction).model_dump()
    return TransactionListItem.model_validate({**read, "share_amount": from_pence(share_pence)})
