"""Sign-in end to end: bearer tokens, automatic landlord creation, settings, isolation."""

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.auth import headers, mint_token

API = "/api/v1"


def test_first_request_creates_the_landlord(client: TestClient) -> None:
    resp = client.get(f"{API}/me", headers=headers("alice", email="alice@example.com"))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["period_basis"] == "standard"


def test_same_subject_is_the_same_landlord(client: TestClient) -> None:
    a = client.get(f"{API}/me", headers=headers("alice")).json()
    b = client.get(f"{API}/me", headers=headers("alice")).json()
    assert a["id"] == b["id"]


def test_no_token_is_401_with_bearer_challenge(client: TestClient) -> None:
    resp = client.get(f"{API}/me")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_bad_tokens_get_the_same_401_whatever_the_reason(client: TestClient) -> None:
    # Telling an attacker *why* a forged token failed would help them fix it.
    expired = {"Authorization": f"Bearer {mint_token('alice', expires_in=-3600)}"}
    garbage = {"Authorization": "Bearer not.a.token"}
    a, b = client.get(f"{API}/me", headers=expired), client.get(f"{API}/me", headers=garbage)
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_update_settings(client: TestClient) -> None:
    resp = client.patch(
        f"{API}/me",
        json={"display_name": "Shaz", "period_basis": "calendar"},
        headers=headers("alice"),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["period_basis"] == "calendar"
    assert client.get(f"{API}/me", headers=headers("alice")).json()["display_name"] == "Shaz"


def test_null_basis_is_422(client: TestClient) -> None:
    resp = client.patch(f"{API}/me", json={"period_basis": None}, headers=headers("alice"))
    assert resp.status_code == 422


def test_saved_basis_becomes_the_tax_default(client: TestClient) -> None:
    client.patch(f"{API}/me", json={"period_basis": "calendar"}, headers=headers("alice"))
    body = client.get(
        f"{API}/tax/obligations", params={"tax_year": 2026}, headers=headers("alice")
    ).json()
    assert body["basis"] == "calendar"
    assert body["obligations"][0]["period_end"] == "2026-06-30"

    explicit = client.get(
        f"{API}/tax/obligations",
        params={"tax_year": 2026, "basis": "standard"},
        headers=headers("alice"),
    ).json()
    assert explicit["basis"] == "standard"


def test_landlords_only_see_their_own_properties(client: TestClient) -> None:
    resp = client.post(
        f"{API}/properties",
        json={
            "nickname": "Elm",
            "address_line_1": "2 Elm Ct",
            "town": "London",
            "postcode": "E1 6AN",
        },
        headers=headers("alice"),
    )
    assert resp.status_code == 201, resp.text
    pid = resp.json()["id"]
    assert client.get(f"{API}/properties/{pid}", headers=headers("bob")).status_code == 404
    assert client.get(f"{API}/properties", headers=headers(str(uuid4()))).json() == []


def test_basis_is_fixed_once_hmrc_accepted_an_update_this_year(
    client: TestClient, db_session
) -> None:
    from datetime import UTC, date, datetime
    from uuid import UUID

    from app.core.time import uk_today
    from app.modules.hmrc.models import HmrcSubmission
    from app.modules.tax.periods import tax_year_containing

    me = client.get(f"{API}/me", headers=headers("alice")).json()
    year = tax_year_containing(uk_today())
    db_session.add(
        HmrcSubmission(
            landlord_id=UUID(me["id"]),
            business_id="XPIS00000000001",
            tax_year=year,
            quarter=1,
            period_start=date(year, 4, 6),
            period_end=date(year, 7, 5),
            consolidated_expenses=False,
            request_body={},
            status_code=204,
            succeeded=True,
            hmrc_correlation_id="ref",
            response_body={},
            submitted_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    resp = client.patch(f"{API}/me", json={"period_basis": "calendar"}, headers=headers("alice"))
    assert resp.status_code == 409
    assert "until the next tax year" in resp.json()["detail"]
    ok = client.patch(f"{API}/me", json={"display_name": "Alice"}, headers=headers("alice"))
    assert ok.status_code == 200
