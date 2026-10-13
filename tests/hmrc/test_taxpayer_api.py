"""NINO, business discovery and obligations over HTTP, with HMRC faked."""

import json
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from tests.auth import headers
from tests.hmrc.fakes import TEST_DEVICE as DEVICE

API = "/api/v1/hmrc"


def signed_in(who: str = "alice") -> dict[str, str]:
    return {**headers(who), "X-LedgerLet-Device": json.dumps(DEVICE)}


def connect(client: TestClient, who: str = "alice") -> None:
    resp = client.post(f"{API}/connect", headers=headers(who))
    state = parse_qs(urlparse(resp.json()["authorize_url"]).query)["state"][0]
    resp = client.get(f"{API}/callback", params={"code": "good-code", "state": state})
    assert resp.headers["location"].endswith("hmrc=connected")


def test_nino_round_trip_is_masked(client: TestClient) -> None:
    resp = client.put(f"{API}/taxpayer", json={"nino": "oe 18 06 77 a"}, headers=headers("alice"))
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"nino": "OE****77A", "uk_property_business_id": None, "sandbox": True}
    assert client.get(f"{API}/taxpayer", headers=headers("alice")).json()["nino"] == "OE****77A"


def test_invalid_nino_is_422(client: TestClient) -> None:
    resp = client.put(f"{API}/taxpayer", json={"nino": "QQ123456C"}, headers=headers("alice"))
    assert resp.status_code == 422


def test_discover_then_obligations(client: TestClient, fake_hmrc_api) -> None:
    connect(client)
    client.put(f"{API}/taxpayer", json={"nino": "OE180677A"}, headers=headers("alice"))

    found = client.post(f"{API}/businesses/discover", headers=signed_in())
    assert found.status_code == 200, found.text
    assert found.json()["selected_business_id"] == "XPIS12345678901"

    obligations = client.get(f"{API}/obligations", params={"tax_year": 2026}, headers=signed_in())
    assert obligations.status_code == 200, obligations.text
    body = obligations.json()
    assert [o["status"] for o in body["obligations"]] == ["fulfilled", "open"]
    assert fake_hmrc_api.calls[-1]["fraud_headers"]["Gov-Client-Device-ID"] == DEVICE["device_id"]


def test_discover_needs_device_details(client: TestClient) -> None:
    connect(client)
    client.put(f"{API}/taxpayer", json={"nino": "OE180677A"}, headers=headers("alice"))
    assert client.post(f"{API}/businesses/discover", headers=headers("alice")).status_code == 422


def test_discover_without_hmrc_connection_is_409(client: TestClient) -> None:
    client.put(f"{API}/taxpayer", json={"nino": "OE180677A"}, headers=headers("alice"))
    assert client.post(f"{API}/businesses/discover", headers=signed_in()).status_code == 409


def test_hmrc_error_is_502_with_hmrc_reference(client: TestClient, fake_hmrc_api) -> None:
    connect(client)
    client.put(f"{API}/taxpayer", json={"nino": "OE180677A"}, headers=headers("alice"))
    fake_hmrc_api.fail_with = (403, {"code": "CLIENT_OR_AGENT_NOT_AUTHORISED", "message": "No"})
    resp = client.post(f"{API}/businesses/discover", headers=signed_in())
    assert resp.status_code == 502
    assert "CLIENT_OR_AGENT_NOT_AUTHORISED" in resp.json()["detail"]
    assert "corr-123" in resp.json()["detail"]


def test_manual_business_choice(client: TestClient) -> None:
    client.put(f"{API}/taxpayer", json={"nino": "OE180677A"}, headers=headers("alice"))
    resp = client.put(
        f"{API}/taxpayer/business",
        json={"business_id": "XPIS12345678901"},
        headers=headers("alice"),
    )
    assert resp.json()["uk_property_business_id"] == "XPIS12345678901"



def test_sandbox_makes_a_test_property_business_and_selects_it(
    client: TestClient, fake_hmrc_api
) -> None:
    connect(client)
    client.put(f"{API}/taxpayer", json={"nino": "OE180677A"}, headers=headers("alice"))
    assert client.get(f"{API}/taxpayer", headers=headers("alice")).json()["sandbox"] is True
    fake_hmrc_api.businesses = []  # HMRC deleted the old one

    resp = client.post(f"{API}/sandbox/property-business", headers=signed_in())
    assert resp.status_code == 200, resp.text
    assert resp.json()["selected_business_id"] == "XPIS99999999999"
    post = next(c for c in fake_hmrc_api.calls if c.get("method") == "POST")
    assert post["fraud_headers"]["Gov-Client-Device-ID"] == DEVICE["device_id"]
