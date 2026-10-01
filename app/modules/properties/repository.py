"""Layer 3, the repository: the only code in this module that writes SQL.

The service asks for things in plain terms ("active property at this address
for this landlord"); this layer works out the query. Every read is scoped by
landlord_id, so one landlord can never load another's data by accident.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.properties.models import Property


class PropertyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, prop: Property) -> Property:
        self._session.add(prop)
        self._session.flush()  # assigns id and defaults without committing
        return prop

    def get_for_landlord(self, landlord_id: UUID, property_id: UUID) -> Property | None:
        stmt = select(Property).where(
            Property.id == property_id,
            Property.landlord_id == landlord_id,
        )
        return self._session.scalars(stmt).one_or_none()

    def list_for_landlord(self, landlord_id: UUID, *, include_archived: bool) -> list[Property]:
        stmt = select(Property).where(Property.landlord_id == landlord_id)
        if not include_archived:
            stmt = stmt.where(Property.archived_at.is_(None))
        stmt = stmt.order_by(func.lower(Property.nickname), Property.created_at)
        return list(self._session.scalars(stmt))

    def find_active_by_address(
        self, landlord_id: UUID, address_line_1: str, postcode: str
    ) -> Property | None:
        stmt = select(Property).where(
            Property.landlord_id == landlord_id,
            Property.archived_at.is_(None),
            Property.postcode == postcode,
            func.lower(Property.address_line_1) == address_line_1.strip().lower(),
        )
        return self._session.scalars(stmt).first()

    def commit(self) -> None:
        self._session.commit()
