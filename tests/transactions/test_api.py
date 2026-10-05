"""End to end over HTTP for transactions."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.transactions.models import Transaction
from tests.auth import headers

PROPERTIES = "/api/v1/properties"
TRANSACTIONS = "/api/v1/transactions"


@pytest.fixture
def property_id(client: TestClient, landlord_id: UUID) -> str:
    resp = client.post(
        PROPERTIES,
        json={
            "nickname": "Elm Court",
            "address_line_1": "2 Elm Court",
            "town": "London",
            "postcode": "SW1A 1AA",
        },
        headers=headers(landlord_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def record(client: TestClient, landlord_id: UUID, property_id: str, **overrides) -> dict:
    body = {
        "transaction_date": "2026-09-01",
        "category": "rental_income",
        "description": "September rent",
        "amount": "850.00",
        **overrides,
    }
    resp = client.post(
        f"{PROPERTIES}/{property_id}/transactions", json=body, headers=headers(landlord_id)
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_categories_endpoint(client) -> None:
    body = client.get(f"{TRANSACTIONS}/categories").json()
    assert len(body) == 12
    by_value = {c["value"]: c for c in body}
    assert by_value["rental_income"]["kind"] == "income"
    assert by_value["residential_finance_costs"]["kind"] == "expense"


def test_record_returns_201(client, landlord_id, property_id) -> None:
    t = record(client, landlord_id, property_id, amount=850.5)
    assert Decimal(t["amount"]) == Decimal("850.50")
    assert t["kind"] == "income"
    assert t["source"] == "manual"
    assert t["is_locked"] is False


def test_invalid_category_is_422(client, landlord_id, property_id) -> None:
    resp = client.post(
        f"{PROPERTIES}/{property_id}/transactions",
        json={
            "transaction_date": "2026-09-01",
            "category": "made_up",
            "description": "x",
            "amount": "1",
        },
        headers=headers(landlord_id),
    )
    assert resp.status_code == 422


def test_future_date_is_422(client, landlord_id, property_id) -> None:
    resp = client.post(
        f"{PROPERTIES}/{property_id}/transactions",
        json={
            "transaction_date": "2999-01-01",
            "category": "rental_income",
            "description": "x",
            "amount": "1",
        },
        headers=headers(landlord_id),
    )
    assert resp.status_code == 422
    assert "future" in resp.json()["detail"]


def test_archived_property_is_409(client, landlord_id, property_id) -> None:
    client.post(f"{PROPERTIES}/{property_id}/archive", headers=headers(landlord_id))
    resp = client.post(
        f"{PROPERTIES}/{property_id}/transactions",
        json={
            "transaction_date": "2026-09-01",
            "category": "rental_income",
            "description": "x",
            "amount": "1",
        },
        headers=headers(landlord_id),
    )
    assert resp.status_code == 409


def test_list_with_filters(client, landlord_id, property_id) -> None:
    record(client, landlord_id, property_id, transaction_date="2026-04-10")
    record(
        client,
        landlord_id,
        property_id,
        transaction_date="2026-07-10",
        category="repairs_and_maintenance",
        description="Boiler",
    )
    url = f"{PROPERTIES}/{property_id}/transactions"

    assert len(client.get(url, headers=headers(landlord_id)).json()) == 2
    repairs = client.get(
        url, params={"category": "repairs_and_maintenance"}, headers=headers(landlord_id)
    ).json()
    assert [t["description"] for t in repairs] == ["Boiler"]
    window = client.get(
        url,
        params={"date_from": "2026-04-01", "date_to": "2026-06-30"},
        headers=headers(landlord_id),
    ).json()
    assert len(window) == 1


def test_other_landlord_cannot_see_or_touch(
    client, landlord_id, other_landlord_id, property_id
) -> None:
    t = record(client, landlord_id, property_id)
    other = headers(other_landlord_id)
    assert client.get(f"{TRANSACTIONS}/{t['id']}", headers=other).status_code == 404
    assert client.delete(f"{TRANSACTIONS}/{t['id']}", headers=other).status_code == 404
    assert client.get(f"{PROPERTIES}/{property_id}/transactions", headers=other).status_code == 404


def test_unknown_transaction_is_404(client, landlord_id) -> None:
    assert client.get(f"{TRANSACTIONS}/{uuid4()}", headers=headers(landlord_id)).status_code == 404


def test_patch_and_delete(client, landlord_id, property_id) -> None:
    t = record(client, landlord_id, property_id)
    resp = client.patch(
        f"{TRANSACTIONS}/{t['id']}", json={"amount": "900"}, headers=headers(landlord_id)
    )
    assert resp.status_code == 200
    assert Decimal(resp.json()["amount"]) == Decimal("900")

    url = f"{TRANSACTIONS}/{t['id']}"
    assert client.delete(url, headers=headers(landlord_id)).status_code == 204
    assert client.get(url, headers=headers(landlord_id)).status_code == 404


def test_locked_transaction_is_409(
    client, db_session: Session, landlord_id, property_id
) -> None:
    t = record(client, landlord_id, property_id)
    row = db_session.get(Transaction, UUID(t["id"]))
    row.locked_at = datetime.now(UTC)  # simulates a submitted quarter
    db_session.commit()

    url = f"{TRANSACTIONS}/{t['id']}"
    resp = client.patch(url, json={"description": "x"}, headers=headers(landlord_id))
    assert resp.status_code == 409
    assert client.delete(url, headers=headers(landlord_id)).status_code == 409
