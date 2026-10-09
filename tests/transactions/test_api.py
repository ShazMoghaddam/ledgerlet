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


def test_locked_transaction_is_409(client, db_session: Session, landlord_id, property_id) -> None:
    t = record(client, landlord_id, property_id)
    row = db_session.get(Transaction, UUID(t["id"]))
    row.locked_at = datetime.now(UTC)  # simulates a submitted quarter
    db_session.commit()

    url = f"{TRANSACTIONS}/{t['id']}"
    resp = client.patch(url, json={"description": "x"}, headers=headers(landlord_id))
    assert resp.status_code == 409
    assert client.delete(url, headers=headers(landlord_id)).status_code == 409


# The cross-property list (GET /transactions). These run the real SQL.


@pytest.fixture
def half_owned_id(client: TestClient, landlord_id: UUID) -> str:
    resp = client.post(
        PROPERTIES,
        json={
            "nickname": "Oak Road",
            "address_line_1": "9 Oak Road",
            "town": "Leeds",
            "postcode": "LS1 1AA",
            "ownership_percentage": "50.00",
        },
        headers=headers(landlord_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.fixture
def both(client, landlord_id, property_id, half_owned_id) -> tuple[str, str]:
    record(client, landlord_id, property_id, transaction_date="2026-10-02", amount="1200.00")
    record(client, landlord_id, half_owned_id, transaction_date="2026-10-01", amount="1600.00")
    record(
        client,
        landlord_id,
        half_owned_id,
        transaction_date="2026-10-03",
        category="repairs_and_maintenance",
        description="Boiler service (100% fix)",
        amount="96.00",
    )
    record(
        client,
        landlord_id,
        property_id,
        transaction_date="2026-10-01",
        category="residential_finance_costs",
        description="Mortgage interest",
        amount="490.00",
    )
    return property_id, half_owned_id


def list_all(client, landlord_id, **params) -> dict:
    resp = client.get(TRANSACTIONS, params=params, headers=headers(landlord_id))
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_list_across_properties(client, landlord_id, both) -> None:
    page = list_all(client, landlord_id)
    assert page["total"] == 4
    assert [i["transaction_date"] for i in page["items"]] == [
        "2026-10-03",
        "2026-10-02",
        "2026-10-01",
        "2026-10-01",
    ]
    boiler = page["items"][0]
    assert (boiler["amount"], boiler["share_amount"]) == ("96.00", "48.00")
    assert (page["money_in"], page["money_out"]) == ("2000.00", "538.00")


def test_list_pages_and_keeps_totals_for_all_matches(client, landlord_id, both) -> None:
    first = list_all(client, landlord_id, limit=3)
    second = list_all(client, landlord_id, limit=3, offset=3)
    ids = [i["id"] for i in first["items"] + second["items"]]
    assert len(ids) == len(set(ids)) == 4
    assert second["money_in"] == first["money_in"] == "2000.00"


def test_list_filters(client, landlord_id, both) -> None:
    _, oak = both
    assert list_all(client, landlord_id, property_id=oak)["total"] == 2
    assert list_all(client, landlord_id, category="rental_income")["total"] == 2
    assert list_all(client, landlord_id, date_from="2026-10-02")["total"] == 2
    assert list_all(client, landlord_id, q="BOILER")["total"] == 1
    assert list_all(client, landlord_id, q="1,200")["total"] == 1
    # % and _ are searched as text, not as SQL wildcards.
    assert list_all(client, landlord_id, q="100%")["total"] == 1
    assert list_all(client, landlord_id, q="%")["total"] == 1


def test_list_is_private_to_each_landlord(client, landlord_id, other_landlord_id, both) -> None:
    _, oak = both
    assert list_all(client, other_landlord_id)["total"] == 0
    resp = client.get(TRANSACTIONS, params={"property_id": oak}, headers=headers(other_landlord_id))
    assert resp.status_code == 404


def test_list_rejects_bad_paging(client, landlord_id) -> None:
    for params in ({"limit": 0}, {"limit": 201}, {"offset": -1}, {"q": "x" * 101}):
        resp = client.get(TRANSACTIONS, params=params, headers=headers(landlord_id))
        assert resp.status_code == 422, params
