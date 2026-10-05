"""Layer 1: the signed-in landlord's own profile."""

from fastapi import APIRouter

from app.modules.landlords.dependencies import CurrentLandlord, LandlordServiceDep
from app.modules.landlords.schemas import LandlordRead, LandlordUpdate

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=LandlordRead)
def get_me(landlord: CurrentLandlord):
    return landlord


@router.patch("", response_model=LandlordRead)
def update_me(payload: LandlordUpdate, landlord: CurrentLandlord, service: LandlordServiceDep):
    return service.update_profile(landlord, payload)
