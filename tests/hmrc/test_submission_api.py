"""Preview, submit and history over HTTP, with real figures from real transactions."""

import json
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from tests.auth import headers
from tests.hmrc.fakes import TEST_DEVICE

API = "/api/v1"


def device(who: str = "alice") -> dict[str, str]:
    return {**headers(who), "X-LedgerLet-Device": json.dumps(TEST_DEVICE)}


def ready_to_file(client: TestClient) -> None:
    """A landlord with a property, a few transactions, HMRC connected, NINO and business."""
    prop = client.post(
        f"{API}/properties",
        json={
            "nickname": "Oak",
            "address_line_1": "9 Oak Road",
            "town": "London",
            "postcode": "E1 6AN",
            "ownership_percentage": "50",
        },
        headers=headers("alice"),
    ).json()
    for day, category, amount in [
        ("2026-05-01", "rental_income", "801.01"),
        ("2026-08-01", "rental_income", "1000.00"),
        ("2026-06-01", "residential_finance_costs", "300.00"),
        ("2026-10-06", "rental_income", "999.00"),  # Q3: must not be in a Q2 update
    ]:
        r = client.post(
            f"{API}/properties/{prop['id']}/transactions",
            json={
                "transaction_date": day,
                "category": category,
                "description": "x",
                "amount": amount,
            },
            headers=headers("alice"),
        )
        assert r.status_code == 201, r.text
    resp = client.post(f"{API}/hmrc/connect", headers=headers("alice"))
    state = parse_qs(urlparse(resp.json()["authorize_url"]).query)["state"][0]
    client.get(f"{API}/hmrc/callback", params={"code": "good-code", "state": state})
    client.put(f"{API}/hmrc/taxpayer", json={"nino": "OE180677A"}, headers=headers("alice"))
    client.put(
        f"{API}/hmrc/taxpayer/business",
        json={"business_id": "XDIS36257256364"},
        headers=headers("alice"),
    )


def test_preview_matches_the_tax_summary(client: TestClient) -> None:
    ready_to_file(client)
    preview = client.post(
        f"{API}/hmrc/submissions/preview",
        json={"tax_year": 2026, "quarter": 2},
        headers=headers("alice"),
    )
    assert preview.status_code == 200, preview.text
    income = preview.json()["body"]["ukProperty"]["income"]["periodAmount"]
    summary = client.get(
        f"{API}/tax/summary", params={"tax_year": 2026, "quarter": 2}, headers=headers("alice")
    ).json()
    # 50% of (801.01 + 1000.00) = 400.51 + 500.00, the October rent excluded
    assert income == 900.51 == float(summary["totals"]["income"])


def test_submit_then_history(client: TestClient, fake_hmrc_api) -> None:
    ready_to_file(client)
    resp = client.post(
        f"{API}/hmrc/submissions", json={"tax_year": 2026, "quarter": 2}, headers=device()
    )
    assert resp.status_code == 201, resp.text  # 2026-27 Q2 ended on 5 October 2026
    assert resp.json()["succeeded"] is True
    history = client.get(f"{API}/hmrc/submissions", headers=headers("alice")).json()
    assert len(history) == 1 and history[0]["quarter"] == 2
    assert fake_hmrc_api.calls[-1]["fraud_headers"]["Gov-Client-Device-ID"]


def test_submit_needs_device_details(client: TestClient) -> None:
    ready_to_file(client)
    resp = client.post(
        f"{API}/hmrc/submissions", json={"tax_year": 2026, "quarter": 2}, headers=headers("alice")
    )
    assert resp.status_code == 422


def test_history_is_per_landlord(client: TestClient) -> None:
    assert client.get(f"{API}/hmrc/submissions", headers=headers("bob")).json() == []
