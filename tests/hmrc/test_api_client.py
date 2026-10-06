"""The real HTTP client's one safety rule, checked without the network."""

import httpx
import pytest

from app.modules.hmrc.api import HttpxHmrcApi


@pytest.fixture
def sent(monkeypatch) -> dict:
    captured: dict = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured.update(url=url, headers=headers)
        return httpx.Response(200, json={}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    return captured


def test_sandbox_sends_the_test_scenario(sent) -> None:
    HttpxHmrcApi("https://test-api.service.hmrc.gov.uk").get(
        "/x", "2.0", "tok", {}, test_scenario="STATEFUL"
    )
    assert sent["headers"]["Gov-Test-Scenario"] == "STATEFUL"
    assert sent["headers"]["Accept"] == "application/vnd.hmrc.2.0+json"


def test_production_never_sends_a_test_scenario(sent) -> None:
    HttpxHmrcApi("https://api.service.hmrc.gov.uk").get(
        "/x", "2.0", "tok", {}, test_scenario="STATEFUL"
    )
    assert "Gov-Test-Scenario" not in sent["headers"]
