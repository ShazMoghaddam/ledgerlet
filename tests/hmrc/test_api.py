"""The HMRC connection over HTTP: start, HMRC's redirect back, status, disconnect."""

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from tests.auth import headers

API = "/api/v1/hmrc"


def start(client: TestClient, who: str = "alice") -> str:
    resp = client.post(f"{API}/connect", headers=headers(who))
    assert resp.status_code == 200, resp.text
    assert "ledgerlet_hmrc_connect" in resp.cookies
    return parse_qs(urlparse(resp.json()["authorize_url"]).query)["state"][0]


def test_full_connection(client: TestClient) -> None:
    state = start(client)
    # HMRC sends the browser back here. No LedgerLet token, just code + state + cookie.
    resp = client.get(f"{API}/callback", params={"code": "good-code", "state": state})
    assert resp.status_code == 200, resp.text
    assert resp.json()["connected"] is True

    status = client.get(f"{API}/connection", headers=headers("alice")).json()
    assert status["connected"] is True
    # Tokens never leave the server.
    assert "access-1" not in str(status) and "refresh-1" not in str(status)


def test_callback_without_the_cookie_is_400(client: TestClient) -> None:
    state = start(client)
    client.cookies.clear()  # a different browser
    resp = client.get(f"{API}/callback", params={"code": "good-code", "state": state})
    assert resp.status_code == 400


def test_landlord_declining_at_hmrc_is_400(client: TestClient) -> None:
    start(client)
    resp = client.get(f"{API}/callback", params={"error": "access_denied"})
    assert resp.status_code == 400
    assert "access_denied" in resp.json()["detail"]


def test_disconnect(client: TestClient) -> None:
    state = start(client)
    client.get(f"{API}/callback", params={"code": "good-code", "state": state})
    assert client.delete(f"{API}/connection", headers=headers("alice")).status_code == 204
    status = client.get(f"{API}/connection", headers=headers("alice")).json()
    assert status == {
        "connected": False,
        "connected_at": None,
        "access_token_expires_at": None,
        "scope": None,
    }


def test_connections_are_per_landlord(client: TestClient) -> None:
    state = start(client, "alice")
    client.get(f"{API}/callback", params={"code": "good-code", "state": state})
    assert client.get(f"{API}/connection", headers=headers("bob")).json()["connected"] is False


def test_connect_requires_sign_in(client: TestClient) -> None:
    assert client.post(f"{API}/connect").status_code == 401
