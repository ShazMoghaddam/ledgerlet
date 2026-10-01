"""Who is making this request?

TEMPORARY STAND-IN. Until the auth module exists, the caller identifies the
landlord with an X-Landlord-Id header. Every endpoint already depends on
`CurrentLandlordId`, so when real authentication lands only this file changes:
no router, service or test needs rewriting.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status


def get_current_landlord_id(
    x_landlord_id: Annotated[UUID | None, Header()] = None,
) -> UUID:
    if x_landlord_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Landlord-Id header",
        )
    return x_landlord_id


CurrentLandlordId = Annotated[UUID, Depends(get_current_landlord_id)]
