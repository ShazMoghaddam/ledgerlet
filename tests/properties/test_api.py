"""End to end through HTTP: routing, validation, error mapping, isolation."""

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from tests.auth import headers

URL = "/api/v1/properties"


def payload(**overrides: object) -> dict[str, object]:
    base = {
        "nickname": "Elm Court",
        "address_line_1": "2 Elm Court",
        "town": "London",
        "postcode": "sw1a1aa",
    }
    return {**base, **overrides}


def create(client: TestClient, landlord_id: UUID, **overrides: object) -> dict:
    resp = client.post(URL, json=payload(**overrides), headers=headers(landlord_id))
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_health(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_create_returns_201_with_normalised_data(client, landlord_id) -> None:
    body = create(client, landlord_id)
    assert body["postcode"] == "SW1A 1AA"
    assert Decimal(body["ownership_percentage"]) == Decimal("100")
    assert body["is_archived"] is False
    assert "landlord_id" not in body


def test_missing_landlord_header_is_401(client) -> None:
    assert client.post(URL, json=payload()).status_code == 401


def test_invalid_postcode_is_422(client, landlord_id) -> None:
    resp = client.post(URL, json=payload(postcode="NOPE"), headers=headers(landlord_id))
    assert resp.status_code == 422


def test_zero_ownership_is_422(client, landlord_id) -> None:
    resp = client.post(
        URL, json=payload(ownership_percentage="0"), headers=headers(landlord_id)
    )
    assert resp.status_code == 422


def test_duplicate_address_is_409(client, landlord_id) -> None:
    create(client, landlord_id)
    resp = client.post(URL, json=payload(), headers=headers(landlord_id))
    assert resp.status_code == 409


def test_other_landlord_gets_404(client, landlord_id, other_landlord_id) -> None:
    prop = create(client, landlord_id)
    resp = client.get(f"{URL}/{prop['id']}", headers=headers(other_landlord_id))
    assert resp.status_code == 404


def test_unknown_id_is_404(client, landlord_id) -> None:
    assert client.get(f"{URL}/{uuid4()}", headers=headers(landlord_id)).status_code == 404


def test_list_only_shows_own_properties(client, landlord_id, other_landlord_id) -> None:
    create(client, landlord_id)
    create(client, other_landlord_id)
    resp = client.get(URL, headers=headers(landlord_id))
    assert len(resp.json()) == 1


def test_patch_updates_fields(client, landlord_id) -> None:
    prop = create(client, landlord_id)
    resp = client.patch(
        f"{URL}/{prop['id']}", json={"nickname": "Renamed"}, headers=headers(landlord_id)
    )
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "Renamed"


def test_patch_null_required_field_is_422(client, landlord_id) -> None:
    prop = create(client, landlord_id)
    resp = client.patch(f"{URL}/{prop['id']}", json={"town": None}, headers=headers(landlord_id))
    assert resp.status_code == 422


def test_archive_restore_lifecycle(client, landlord_id) -> None:
    prop = create(client, landlord_id)
    pid = prop["id"]

    archived = client.post(f"{URL}/{pid}/archive", headers=headers(landlord_id)).json()
    assert archived["is_archived"] is True

    assert client.get(URL, headers=headers(landlord_id)).json() == []
    all_props = client.get(URL, params={"include_archived": True}, headers=headers(landlord_id))
    assert len(all_props.json()) == 1

    resp = client.patch(f"{URL}/{pid}", json={"nickname": "x"}, headers=headers(landlord_id))
    assert resp.status_code == 409

    restored = client.post(f"{URL}/{pid}/restore", headers=headers(landlord_id)).json()
    assert restored["is_archived"] is False
