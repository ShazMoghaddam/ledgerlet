"""Business rules, tested in isolation with the fake repository (no database)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.properties.schemas import PropertyCreate, PropertyUpdate
from app.modules.properties.service import PropertyService
from tests.properties.fakes import FakePropertyRepository

FROZEN = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def make_create(**overrides: object) -> PropertyCreate:
    base = {
        "nickname": "Elm Court",
        "address_line_1": "2 Elm Court",
        "town": "London",
        "postcode": "SW1A 1AA",
    }
    return PropertyCreate(**{**base, **overrides})


@pytest.fixture
def repo() -> FakePropertyRepository:
    return FakePropertyRepository()


@pytest.fixture
def service(repo: FakePropertyRepository) -> PropertyService:
    return PropertyService(repo, clock=lambda: FROZEN)


def test_create_saves_and_commits(service: PropertyService, repo, landlord_id: UUID) -> None:
    prop = service.create_property(landlord_id, make_create())
    assert prop.id in repo.items
    assert prop.landlord_id == landlord_id
    assert repo.commit_count == 1


def test_create_rejects_duplicate_active_address(service, landlord_id) -> None:
    service.create_property(landlord_id, make_create())
    with pytest.raises(ConflictError):
        service.create_property(landlord_id, make_create(address_line_1="2 ELM COURT"))


def test_same_address_allowed_for_different_landlords(
    service, landlord_id, other_landlord_id
) -> None:
    service.create_property(landlord_id, make_create())
    service.create_property(other_landlord_id, make_create())  # no error


def test_get_other_landlords_property_is_not_found(
    service, landlord_id, other_landlord_id
) -> None:
    prop = service.create_property(landlord_id, make_create())
    with pytest.raises(NotFoundError):
        service.get_property(other_landlord_id, prop.id)


def test_get_missing_property_is_not_found(service, landlord_id) -> None:
    with pytest.raises(NotFoundError):
        service.get_property(landlord_id, uuid4())


def test_update_changes_only_sent_fields(service, landlord_id) -> None:
    prop = service.create_property(landlord_id, make_create())
    updated = service.update_property(landlord_id, prop.id, PropertyUpdate(nickname="Renamed"))
    assert updated.nickname == "Renamed"
    assert updated.town == "London"


def test_update_to_own_address_is_not_a_duplicate(service, landlord_id) -> None:
    prop = service.create_property(landlord_id, make_create())
    service.update_property(landlord_id, prop.id, PropertyUpdate(postcode="SW1A 1AA"))


def test_update_into_another_propertys_address_conflicts(service, landlord_id) -> None:
    service.create_property(landlord_id, make_create())
    second = service.create_property(
        landlord_id, make_create(nickname="Oak", address_line_1="9 Oak Road")
    )
    with pytest.raises(ConflictError):
        service.update_property(
            landlord_id, second.id, PropertyUpdate(address_line_1="2 Elm Court")
        )


def test_archive_sets_timestamp_from_clock(service, landlord_id) -> None:
    prop = service.create_property(landlord_id, make_create())
    archived = service.archive_property(landlord_id, prop.id)
    assert archived.is_archived
    assert archived.archived_at == FROZEN


def test_archive_is_idempotent(service, repo, landlord_id) -> None:
    prop = service.create_property(landlord_id, make_create())
    service.archive_property(landlord_id, prop.id)
    commits = repo.commit_count
    service.archive_property(landlord_id, prop.id)
    assert repo.commit_count == commits  # second archive is a no-op


def test_archived_property_cannot_be_edited(service, landlord_id) -> None:
    prop = service.create_property(landlord_id, make_create())
    service.archive_property(landlord_id, prop.id)
    with pytest.raises(ConflictError):
        service.update_property(landlord_id, prop.id, PropertyUpdate(nickname="Nope"))


def test_archiving_frees_the_address(service, landlord_id) -> None:
    prop = service.create_property(landlord_id, make_create())
    service.archive_property(landlord_id, prop.id)
    service.create_property(landlord_id, make_create())  # allowed now


def test_restore_blocked_if_address_reused(service, landlord_id) -> None:
    old = service.create_property(landlord_id, make_create())
    service.archive_property(landlord_id, old.id)
    service.create_property(landlord_id, make_create())
    with pytest.raises(ConflictError):
        service.restore_property(landlord_id, old.id)


def test_restore_clears_archive(service, landlord_id) -> None:
    prop = service.create_property(landlord_id, make_create())
    service.archive_property(landlord_id, prop.id)
    restored = service.restore_property(landlord_id, prop.id)
    assert not restored.is_archived


def test_list_hides_archived_by_default(service, landlord_id) -> None:
    keep = service.create_property(landlord_id, make_create(nickname="Keep"))
    gone = service.create_property(
        landlord_id, make_create(nickname="Gone", address_line_1="1 Other St")
    )
    service.archive_property(landlord_id, gone.id)

    assert [p.id for p in service.list_properties(landlord_id)] == [keep.id]
    assert len(service.list_properties(landlord_id, include_archived=True)) == 2
