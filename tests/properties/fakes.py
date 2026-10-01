"""In-memory stand-in for PropertyRepository.

It satisfies PropertyRepositoryProtocol, which is all the service asks for.
That's the payoff of layering: business rules are tested with no database.
"""

from uuid import UUID, uuid4

from app.core.time import utc_now
from app.modules.properties.models import Property


class FakePropertyRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Property] = {}
        self.commit_count = 0

    def add(self, prop: Property) -> Property:
        if prop.id is None:
            prop.id = uuid4()
        now = utc_now()
        prop.created_at = prop.created_at or now
        prop.updated_at = prop.updated_at or now
        self.items[prop.id] = prop
        return prop

    def get_for_landlord(self, landlord_id: UUID, property_id: UUID) -> Property | None:
        prop = self.items.get(property_id)
        return prop if prop is not None and prop.landlord_id == landlord_id else None

    def list_for_landlord(self, landlord_id: UUID, *, include_archived: bool) -> list[Property]:
        props = [
            p
            for p in self.items.values()
            if p.landlord_id == landlord_id and (include_archived or p.archived_at is None)
        ]
        return sorted(props, key=lambda p: (p.nickname.lower(), p.created_at))

    def find_active_by_address(
        self, landlord_id: UUID, address_line_1: str, postcode: str
    ) -> Property | None:
        wanted = address_line_1.strip().lower()
        for p in self.items.values():
            if (
                p.landlord_id == landlord_id
                and p.archived_at is None
                and p.postcode == postcode
                and p.address_line_1.lower() == wanted
            ):
                return p
        return None

    def commit(self) -> None:
        self.commit_count += 1
