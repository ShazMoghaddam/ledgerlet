"""End to end over HTTP for the tax endpoints."""

from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

API = "/api/v1"


def headers(landlord_id: UUID) -> dict[str, str]:
    return {"X-Landlord-Id": str(landlord_id)}


@pytest.fixture
def joint_property(client: TestClient, landlord_id: UUID) -> str:
    resp = client.post(
        f"{API}/properties",
        json={
            "nickname": "Oak Road",
            "address_line_1": "9 Oak Road",
            "town": "London",
            "postcode": "E1 6AN",
            "ownership_percentage": "50",
        },
        headers=headers(landlord_id),
    )
    assert resp.status_code == 201, resp.text
    pid = resp.json()["id"]
    for day, category, amount in [
        ("2026-05-01", "rental_income", "1000.00"),
        ("2026-05-02", "repairs_and_maintenance", "100.01"),
        ("2026-08-01", "rental_income", "1000.00"),
    ]:
        r = client.post(
            f"{API}/properties/{pid}/transactions",
            json={
                "transaction_date": day,
                "category": category,
                "description": "x",
                "amount": amount,
            },
            headers=headers(landlord_id),
        )
        assert r.status_code == 201, r.text
    return pid


def test_obligations(client, landlord_id) -> None:
    resp = client.get(
        f"{API}/tax/obligations", params={"tax_year": 2026}, headers=headers(landlord_id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tax_year_label"] == "2026-27"
    assert [o["deadline"] for o in body["obligations"]] == [
        "2026-08-07",
        "2026-11-07",
        "2027-02-07",
        "2027-05-07",
    ]


def test_calendar_obligations(client, landlord_id) -> None:
    body = client.get(
        f"{API}/tax/obligations",
        params={"tax_year": 2026, "basis": "calendar"},
        headers=headers(landlord_id),
    ).json()
    assert body["obligations"][0]["period_end"] == "2026-06-30"


def test_summary_applies_share(client, landlord_id, joint_property) -> None:
    resp = client.get(
        f"{API}/tax/summary",
        params={"tax_year": 2026, "quarter": 1},
        headers=headers(landlord_id),
    )
    assert resp.status_code == 200, resp.text
    totals = resp.json()["totals"]
    assert Decimal(totals["income"]) == Decimal("500.00")
    assert Decimal(totals["expenses"]) == Decimal("50.01")  # 50.005 rounds half up
    assert Decimal(totals["profit"]) == Decimal("449.99")


def test_summary_q2_is_cumulative(client, landlord_id, joint_property) -> None:
    body = client.get(
        f"{API}/tax/summary",
        params={"tax_year": 2026, "quarter": 2},
        headers=headers(landlord_id),
    ).json()
    assert Decimal(body["totals"]["income"]) == Decimal("1000.00")


@pytest.mark.parametrize("quarter", [0, 5])
def test_invalid_quarter_is_422(client, landlord_id, quarter) -> None:
    resp = client.get(
        f"{API}/tax/summary", params={"quarter": quarter}, headers=headers(landlord_id)
    )
    assert resp.status_code == 422


def test_requires_landlord(client) -> None:
    assert client.get(f"{API}/tax/obligations").status_code == 401
