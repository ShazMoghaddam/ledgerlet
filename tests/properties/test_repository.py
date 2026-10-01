"""Repository against a real database: queries, scoping and constraints."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.properties.models import Property
from app.modules.properties.repository import PropertyRepository


def make_property(landlord_id: UUID, **overrides: object) -> Property:
    fields = {
        "landlord_id": landlord_id,
        "nickname": "Elm Court",
        "address_line_1": "2 Elm Court",
        "town": "London",
        "postcode": "SW1A 1AA",
        "ownership_percentage": Decimal("100.00"),
    }
    return Property(**{**fields, **overrides})


@pytest.fixture
def repo(db_session: Session) -> PropertyRepository:
    return PropertyRepository(db_session)


def test_add_assigns_id_and_timestamps(repo, landlord_id) -> None:
    prop = repo.add(make_property(landlord_id))
    repo.commit()
    assert prop.id is not None
    assert prop.created_at is not None


def test_get_is_scoped_to_landlord(repo, landlord_id, other_landlord_id) -> None:
    prop = repo.add(make_property(landlord_id))
    repo.commit()
    assert repo.get_for_landlord(landlord_id, prop.id) is not None
    assert repo.get_for_landlord(other_landlord_id, prop.id) is None


def test_list_orders_by_nickname_and_hides_archived(repo, landlord_id) -> None:
    repo.add(make_property(landlord_id, nickname="beta", address_line_1="2 B St"))
    repo.add(make_property(landlord_id, nickname="Alpha", address_line_1="1 A St"))
    repo.add(
        make_property(
            landlord_id,
            nickname="Archived",
            address_line_1="3 C St",
            archived_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    repo.commit()

    active = repo.list_for_landlord(landlord_id, include_archived=False)
    assert [p.nickname for p in active] == ["Alpha", "beta"]
    assert len(repo.list_for_landlord(landlord_id, include_archived=True)) == 3


def test_find_active_by_address_is_case_insensitive(repo, landlord_id) -> None:
    repo.add(make_property(landlord_id))
    repo.commit()
    assert repo.find_active_by_address(landlord_id, "2 ELM COURT", "SW1A 1AA") is not None
    assert repo.find_active_by_address(landlord_id, "2 Elm Court", "EC1A 1BB") is None


def test_find_active_by_address_ignores_archived(repo, landlord_id) -> None:
    repo.add(make_property(landlord_id, archived_at=datetime(2026, 1, 1, tzinfo=UTC)))
    repo.commit()
    assert repo.find_active_by_address(landlord_id, "2 Elm Court", "SW1A 1AA") is None


def test_database_rejects_out_of_range_ownership(repo, db_session, landlord_id) -> None:
    with pytest.raises(IntegrityError):
        repo.add(make_property(landlord_id, ownership_percentage=Decimal("0")))
    db_session.rollback()
