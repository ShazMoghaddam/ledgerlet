"""HMRC's MTD APIs (user-restricted calls). Endpoints and versions live here, in one place.

Versions match the subscriptions on LedgerLet's Developer Hub application. If HMRC
moves a path or version, it's a one-line change below.
"""

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

BUSINESS_DETAILS_VERSION = "2.0"
OBLIGATIONS_VERSION = "3.0"
PROPERTY_BUSINESS_VERSION = "6.0"

LIST_BUSINESSES = "/individuals/business/details/{nino}/list"
OBLIGATIONS = "/obligations/details/{nino}/income-and-expenditure"

TIMEOUT_SECONDS = 20.0

# HMRC's sandbox returns canned example data unless asked for the "stateful" view,
# which reflects test data we created (e.g. via the Test Support API).
STATEFUL = "STATEFUL"


@dataclass(frozen=True)
class HmrcResponse:
    status_code: int
    body: dict[str, Any]
    correlation_id: str | None  # HMRC's reference for this call; quote it to HMRC support

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class HmrcApi(Protocol):
    def get(
        self,
        path: str,
        version: str,
        access_token: str,
        fraud_headers: dict[str, str],
        params: dict[str, str] | None = None,
        test_scenario: str | None = None,
    ) -> HmrcResponse: ...


class HttpxHmrcApi:
    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")
        self._sandbox = "test-api." in self._base

    def get(
        self,
        path: str,
        version: str,
        access_token: str,
        fraud_headers: dict[str, str],
        params: dict[str, str] | None = None,
        test_scenario: str | None = None,
    ) -> HmrcResponse:
        headers = {
            **fraud_headers,
            "Authorization": f"Bearer {access_token}",
            "Accept": f"application/vnd.hmrc.{version}+json",
        }
        if test_scenario and self._sandbox:  # never sent to production, whatever the caller asks
            headers["Gov-Test-Scenario"] = test_scenario
        response = httpx.get(
            f"{self._base}{path}", headers=headers, params=params, timeout=TIMEOUT_SECONDS
        )
        try:
            body = response.json() if response.content else {}
        except ValueError:
            body = {"raw": response.text[:500]}
        return HmrcResponse(
            status_code=response.status_code,
            body=body if isinstance(body, dict) else {"items": body},
            correlation_id=response.headers.get("X-CorrelationId"),
        )
