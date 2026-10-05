"""End to end: multipart upload, preview, confirm, re-import."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from tests.auth import headers

PROPERTIES = "/api/v1/properties"
STATEMENT = (
    b"Date,Description,Amount\n"
    b"01/09/2026,J SMITH RENT,850.00\n"
    b"03/09/2026,BRITISH GAS,-62.40\n"
    b"05/09/2026,BAD ROW,abc\n"
)
MAPPING = {"date_column": "Date", "description_column": "Description", "amount_column": "Amount"}
CATEGORIES = {"J SMITH RENT": "rental_income", "BRITISH GAS": "premises_running_costs"}


@pytest.fixture
def property_id(client: TestClient, landlord_id: UUID) -> str:
    resp = client.post(
        PROPERTIES,
        json={
            "nickname": "Elm",
            "address_line_1": "2 Elm Court",
            "town": "London",
            "postcode": "E1 6AN",
        },
        headers=headers(landlord_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def preview(client, landlord_id, property_id, content=STATEMENT, mapping=None):
    return client.post(
        f"{PROPERTIES}/{property_id}/imports/preview",
        files={"file": ("statement.csv", content, "text/csv")},
        data=mapping or MAPPING,
        headers=headers(landlord_id),
    )


def to_confirm(preview_body: dict) -> dict:
    return {
        "rows": [
            {
                "fingerprint": r["fingerprint"],
                "transaction_date": r["transaction_date"],
                "description": r["description"],
                "amount": r["amount"],
                "direction": r["direction"],
                "category": CATEGORIES[r["description"]],
            }
            for r in preview_body["rows"]
            if r["fingerprint"]
        ]
    }


def test_preview_upload(client, landlord_id, property_id) -> None:
    resp = preview(client, landlord_id, property_id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (body["total"], body["new"], body["invalid"]) == (3, 2, 1)
    assert [r["status"] for r in body["rows"]] == ["new", "new", "invalid"]
    assert body["rows"][0]["suggested_kind"] == "income"


def test_full_round_trip_then_reimport(client, landlord_id, property_id) -> None:
    body = preview(client, landlord_id, property_id).json()
    url = f"{PROPERTIES}/{property_id}/imports/confirm"

    resp = client.post(url, json=to_confirm(body), headers=headers(landlord_id))
    assert resp.status_code == 201, resp.text
    assert resp.json()["created"] == 2

    listed = client.get(
        f"{PROPERTIES}/{property_id}/transactions", headers=headers(landlord_id)
    ).json()
    assert {t["source"] for t in listed} == {"csv_import"}

    again = preview(client, landlord_id, property_id).json()
    assert again["already_imported"] == 2
    resp = client.post(url, json=to_confirm(again), headers=headers(landlord_id))
    assert resp.json() == {"created": 0, "skipped_already_imported": 2, "transaction_ids": []}


def test_invalid_mapping_is_422(client, landlord_id, property_id) -> None:
    bad = {"date_column": "Date", "description_column": "Description"}  # no amount columns
    resp = preview(client, landlord_id, property_id, mapping=bad)
    assert resp.status_code == 422


def test_missing_column_is_422_with_helpful_message(client, landlord_id, property_id) -> None:
    resp = preview(client, landlord_id, property_id, content=b"Date,Memo,Amount\n01/09/2026,A,1\n")
    assert resp.status_code == 422
    assert "Memo" in resp.json()["detail"]


def test_wrong_category_direction_is_422(client, landlord_id, property_id) -> None:
    body = to_confirm(preview(client, landlord_id, property_id).json())
    body["rows"][1]["category"] = "rental_income"  # money out tagged as income
    resp = client.post(
        f"{PROPERTIES}/{property_id}/imports/confirm", json=body, headers=headers(landlord_id)
    )
    assert resp.status_code == 422


def test_bad_fingerprint_is_422(client, landlord_id, property_id) -> None:
    body = to_confirm(preview(client, landlord_id, property_id).json())
    body["rows"][0]["fingerprint"] = "not-a-hash"
    resp = client.post(
        f"{PROPERTIES}/{property_id}/imports/confirm", json=body, headers=headers(landlord_id)
    )
    assert resp.status_code == 422


def test_other_landlord_gets_404(client, other_landlord_id, property_id) -> None:
    assert preview(client, other_landlord_id, property_id).status_code == 404
