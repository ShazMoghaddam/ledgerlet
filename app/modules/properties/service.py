"""Layer 2, the service: LedgerLet's business rules for properties.

Knows nothing about HTTP or SQL. It depends on the *shape* of a repository
(PropertyRepositoryProtocol), not the real one, so tests can hand it an
in-memory fake and exercise every rule without a database.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import utc_now
from app.modules.properties.models import Property
from app.modules.properties.schemas import PropertyCreate, PropertyUpdate


class PropertyRepositoryProtocol(Protocol):
    def add(self, prop: Property) -> Property: ...
    def get_for_landlord(self, landlord_id: UUID, property_id: UUID) -> Property | None: ...
    def list_for_landlord(
        self, landlord_id: UUID, *, include_archived: bool
    ) -> list[Property]: ...
    def find_active_by_address(
        self, landlord_id: UUID, address_line_1: str, postcode: str
    ) -> Property | None: ...
    def commit(self) -> None: ...


class PropertyService:
    def __init__(
        self,
        repository: PropertyRepositoryProtocol,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._repo = repository
        self._clock = clock

    # Queries

    def get_property(self, landlord_id: UUID, property_id: UUID) -> Property:
        prop = self._repo.get_for_landlord(landlord_id, property_id)
        if prop is None:
            # Same error whether it doesn't exist or belongs to someone else,
            # so the API never leaks the existence of other landlords' data.
            raise NotFoundError(f"Property {property_id} not found")
        return prop

    def list_properties(
        self, landlord_id: UUID, *, include_archived: bool = False
    ) -> list[Property]:
        return self._repo.list_for_landlord(landlord_id, include_archived=include_archived)

    # Commands

    def create_property(self, landlord_id: UUID, data: PropertyCreate) -> Property:
        self._ensure_address_is_free(landlord_id, data.address_line_1, data.postcode)
        prop = Property(landlord_id=landlord_id, **data.model_dump())
        self._repo.add(prop)
        self._repo.commit()
        return prop

    def update_property(
        self, landlord_id: UUID, property_id: UUID, data: PropertyUpdate
    ) -> Property:
        prop = self.get_property(landlord_id, property_id)
        if prop.is_archived:
            raise ConflictError("Archived properties cannot be edited. Restore it first.")

        changes = data.model_dump(exclude_unset=True)
        if "address_line_1" in changes or "postcode" in changes:
            self._ensure_address_is_free(
                landlord_id,
                changes.get("address_line_1", prop.address_line_1),
                changes.get("postcode", prop.postcode),
                ignore_id=prop.id,
            )

        for field, value in changes.items():
            setattr(prop, field, value)
        self._repo.commit()
        return prop

    def archive_property(self, landlord_id: UUID, property_id: UUID) -> Property:
        prop = self.get_property(landlord_id, property_id)
        if not prop.is_archived:  # idempotent: archiving twice keeps the original date
            prop.archived_at = self._clock()
            self._repo.commit()
        return prop

    def restore_property(self, landlord_id: UUID, property_id: UUID) -> Property:
        prop = self.get_property(landlord_id, property_id)
        if prop.is_archived:
            self._ensure_address_is_free(
                landlord_id, prop.address_line_1, prop.postcode, ignore_id=prop.id
            )
            prop.archived_at = None
            self._repo.commit()
        return prop

    # Rules

    def _ensure_address_is_free(
        self,
        landlord_id: UUID,
        address_line_1: str,
        postcode: str,
        ignore_id: UUID | None = None,
    ) -> None:
        existing = self._repo.find_active_by_address(landlord_id, address_line_1, postcode)
        if existing is not None and existing.id != ignore_id:
            raise ConflictError(
                f"You already have an active property at {address_line_1}, {postcode}"
            )
