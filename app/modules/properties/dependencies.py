"""Per-request wiring: a fresh repository and service bound to this request's session."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.properties.repository import PropertyRepository
from app.modules.properties.service import PropertyService


def get_property_service(db: Annotated[Session, Depends(get_db)]) -> PropertyService:
    return PropertyService(PropertyRepository(db))


PropertyServiceDep = Annotated[PropertyService, Depends(get_property_service)]
