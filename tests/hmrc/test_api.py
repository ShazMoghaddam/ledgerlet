"""The HMRC connection over HTTP: start, HMRC's redirect back, status, disconnect."""

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from tests.auth import headers

API = "/api/v1/hmrc"


APP = "http://localhost:5173"


def start(client: TestClient, who: str = "alice", **body) -> str:
    resp = client.post(f"{API}/connect", headers=headers(who), json=body or None)
    assert resp.status_code == 200, resp.text
    assert "ledgerlet_hmrc_connect" in resp.cookies
    return parse_qs(urlparse(resp.json()["authorize_url"]).query)["state"][0]


def test_full_connection(client: TestClient) -> None:
    state = start(client)
    # HMRC sends the browser back here. No LedgerLet token, just code + state + cookie.
    resp = client.get(f"{API}/callback", params={"code": "good-code", "state": state})
    # ...and we send the browser back into the web app.
    assert resp.status_code == 303, resp.text
    assert resp.headers["location"] == f"{APP}/settings/hmrc?hmrc=connected"
    assert 'ledgerlet_hmrc_connect=""' in resp.headers["set-cookie"]  # cookie cleared

    status = client.get(f"{API}/connection", headers=headers("alice")).json()
    assert status["connected"] is True
    # Tokens never leave the server.
    assert "access-1" not in str(status) and "refresh-1" not in str(status)


def test_callback_without_the_cookie_goes_back_with_an_error(client: TestClient) -> None:
    state = start(client)
    client.cookies.clear()  # a different browser
    resp = client.get(f"{API}/callback", params={"code": "good-code", "state": state})
    assert resp.headers["location"] == f"{APP}/settings/hmrc?hmrc=error&reason=other_browser"
    assert client.get(f"{API}/connection", headers=headers("alice")).json()["connected"] is False


def test_landlord_declining_at_hmrc(client: TestClient) -> None:
    start(client)
    resp = client.get(f"{API}/callback", params={"error": "access_denied"})
    assert resp.headers["location"] == f"{APP}/settings/hmrc?hmrc=error&reason=declined"


def test_callback_with_nothing_useful(client: TestClient) -> None:
    resp = client.get(f"{API}/callback")
    assert resp.headers["location"] == f"{APP}/settings/hmrc?hmrc=error&reason=invalid"


def test_landlord_returns_to_where_they_started(client: TestClient) -> None:
    state = start(client, return_to="/tax/2026/q2/submit?step=3")
    resp = client.get(f"{API}/callback", params={"code": "good-code", "state": state})
    assert resp.headers["location"] == f"{APP}/tax/2026/q2/submit?step=3&hmrc=connected"


@pytest.mark.parametrize(
    "return_to",
    ["https://evil.example", "//evil.example", "/\\evil.example", "evil", "/a b", "/" + "a" * 200],
)
def test_return_path_must_be_inside_the_app(client: TestClient, return_to: str) -> None:
    resp = client.post(f"{API}/connect", headers=headers("alice"), json={"return_to": return_to})
    assert resp.status_code == 422


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
