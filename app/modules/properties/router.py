"""Layer 1, the API: HTTP in, HTTP out. No business logic lives here.

Each endpoint does three things: accept a validated request, call one service
method, return the result. Domain errors are turned into status codes by
app/core/error_handlers.py.
"""

from uuid import UUID

from fastapi import APIRouter, status

from app.core.security import CurrentLandlordId
from app.modules.properties.dependencies import PropertyServiceDep
from app.modules.properties.schemas import PropertyCreate, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyCreate, landlord_id: CurrentLandlordId, service: PropertyServiceDep
):
    return service.create_property(landlord_id, payload)


@router.get("", response_model=list[PropertyRead])
def list_properties(
    landlord_id: CurrentLandlordId, service: PropertyServiceDep, include_archived: bool = False
):
    return service.list_properties(landlord_id, include_archived=include_archived)


@router.get("/{property_id}", response_model=PropertyRead)
def get_property(property_id: UUID, landlord_id: CurrentLandlordId, service: PropertyServiceDep):
    return service.get_property(landlord_id, property_id)


@router.patch("/{property_id}", response_model=PropertyRead)
def update_property(
    property_id: UUID,
    payload: PropertyUpdate,
    landlord_id: CurrentLandlordId,
    service: PropertyServiceDep,
):
    return service.update_property(landlord_id, property_id, payload)


@router.post("/{property_id}/archive", response_model=PropertyRead)
def archive_property(
    property_id: UUID, landlord_id: CurrentLandlordId, service: PropertyServiceDep
):
    return service.archive_property(landlord_id, property_id)


@router.post("/{property_id}/restore", response_model=PropertyRead)
def restore_property(
    property_id: UUID, landlord_id: CurrentLandlordId, service: PropertyServiceDep
):
    return service.restore_property(landlord_id, property_id)
