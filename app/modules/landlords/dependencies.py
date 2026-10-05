"""Who is making this request? Every protected endpoint depends on this.

Bearer token -> verified identity (core/auth.py) -> landlord row (created on
first sign-in). Routers ask for CurrentLandlordId, or CurrentLandlord when they
also need the landlord's settings.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth import InvalidTokenError, TokenVerifier, get_token_verifier
from app.core.database import get_db
from app.modules.landlords.models import Landlord
from app.modules.landlords.repository import LandlordRepository
from app.modules.landlords.service import LandlordService

_bearer = HTTPBearer(auto_error=False)

_UNAUTHORISED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not signed in, or the sign-in has expired",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_landlord_service(db: Annotated[Session, Depends(get_db)]) -> LandlordService:
    return LandlordService(LandlordRepository(db))


LandlordServiceDep = Annotated[LandlordService, Depends(get_landlord_service)]


def get_current_landlord(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
    service: LandlordServiceDep,
) -> Landlord:
    if credentials is None:
        raise _UNAUTHORISED
    try:
        identity = verifier.verify(credentials.credentials)
    except InvalidTokenError:
        # The reason (expired, bad signature...) is deliberately not returned.
        raise _UNAUTHORISED from None
    return service.sign_in(identity)


CurrentLandlord = Annotated[Landlord, Depends(get_current_landlord)]


def get_current_landlord_id(landlord: CurrentLandlord) -> UUID:
    return landlord.id


CurrentLandlordId = Annotated[UUID, Depends(get_current_landlord_id)]
