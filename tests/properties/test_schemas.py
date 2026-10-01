from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.properties.schemas import PropertyCreate, PropertyUpdate

VALID = {
    "nickname": "Elm Court",
    "address_line_1": "2 Elm Court",
    "town": "London",
    "postcode": "sw1a1aa",
}


def test_create_normalises_postcode_and_defaults_full_ownership() -> None:
    data = PropertyCreate(**VALID)
    assert data.postcode == "SW1A 1AA"
    assert data.ownership_percentage == Decimal("100")


def test_create_strips_whitespace() -> None:
    data = PropertyCreate(**{**VALID, "nickname": "  Elm Court  "})
    assert data.nickname == "Elm Court"


@pytest.mark.parametrize("pct", ["0", "-5", "100.01", "33.333"])
def test_create_rejects_bad_ownership_percentage(pct: str) -> None:
    with pytest.raises(ValidationError):
        PropertyCreate(**{**VALID, "ownership_percentage": pct})


def test_create_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        PropertyCreate(**{**VALID, "landlord_id": "someone-else"})


def test_update_only_tracks_fields_sent() -> None:
    data = PropertyUpdate(nickname="New name")
    assert data.model_dump(exclude_unset=True) == {"nickname": "New name"}


def test_update_rejects_null_for_required_field() -> None:
    with pytest.raises(ValidationError):
        PropertyUpdate(nickname=None)


def test_update_allows_clearing_address_line_2() -> None:
    data = PropertyUpdate(address_line_2=None)
    assert data.model_dump(exclude_unset=True) == {"address_line_2": None}
