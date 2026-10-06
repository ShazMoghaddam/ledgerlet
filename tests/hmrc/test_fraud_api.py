"""The validate endpoint, the device header, and proxy handling."""

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.modules.hmrc.dependencies as deps
from tests.auth import headers
from tests.hmrc.fakes import TEST_DEVICE

URL = "/api/v1/hmrc/fraud-headers/validate"
DEVICE = TEST_DEVICE


def with_device(who: str = "alice", device: dict | str = DEVICE) -> dict[str, str]:
    raw = device if isinstance(device, str) else json.dumps(device)
    return {**headers(who), "X-LedgerLet-Device": raw}


def test_builds_headers_and_returns_hmrc_verdict(client: TestClient, fake_fraud_validator) -> None:
    me = client.get("/api/v1/me", headers=headers("alice")).json()
    resp = client.post(URL, headers=with_device())
    assert resp.status_code == 200, resp.text
    sent = resp.json()["headers_sent"]
    assert sent["Gov-Client-Connection-Method"] == "WEB_APP_VIA_SERVER"
    assert sent["Gov-Client-Device-ID"] == DEVICE["device_id"]
    assert sent["Gov-Client-User-IDs"] == f"ledgerlet={me['id']}"
    assert sent["Gov-Client-Timezone"] == "UTC+01:00"
    assert resp.json()["hmrc_response"]["code"] == "VALID_HEADERS"
    assert fake_fraud_validator.received == [sent]  # exactly what HMRC was sent


def test_missing_device_header_is_422(client: TestClient) -> None:
    resp = client.post(URL, headers=headers("alice"))
    assert resp.status_code == 422
    assert "X-LedgerLet-Device" in resp.json()["detail"]


def test_malformed_device_json_is_422(client: TestClient) -> None:
    assert client.post(URL, headers=with_device(device="{not json")).status_code == 422


def test_unexpected_device_fields_are_422(client: TestClient) -> None:
    bad = {**DEVICE, "screens": [], "extra": 1}
    assert client.post(URL, headers=with_device(device=bad)).status_code == 422


def test_requires_sign_in(client: TestClient) -> None:
    assert client.post(URL, headers={"X-LedgerLet-Device": json.dumps(DEVICE)}).status_code == 401


def test_device_probe_page(client: TestClient) -> None:
    resp = client.get("/api/v1/hmrc/dev/device")
    assert resp.status_code == 200
    assert "ledgerlet-device-id" in resp.text


def _request(host: str, forwarded: str | None = None) -> SimpleNamespace:
    hdrs = {"x-forwarded-for": forwarded} if forwarded else {}
    return SimpleNamespace(client=SimpleNamespace(host=host, port=4321), headers=hdrs)


def test_forwarded_ip_ignored_unless_proxy_is_trusted(monkeypatch) -> None:
    settings = SimpleNamespace(trust_proxy_headers=False, hmrc_vendor_public_ip=None)
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    ctx = deps.get_server_context(_request("10.0.0.5", "203.0.113.9"))
    assert ctx.client_public_ip == "10.0.0.5"  # a client can't spoof its IP via a header


def test_forwarded_ip_used_behind_our_proxy(monkeypatch) -> None:
    settings = SimpleNamespace(trust_proxy_headers=True, hmrc_vendor_public_ip="198.51.100.1")
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    ctx = deps.get_server_context(_request("10.0.0.5", "203.0.113.9, 10.0.0.1"))
    assert ctx.client_public_ip == "203.0.113.9"
    assert ctx.vendor_public_ip == "198.51.100.1"
