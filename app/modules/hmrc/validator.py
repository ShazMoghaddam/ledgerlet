"""HMRC's Test Fraud Prevention Headers API: HMRC tells us whether our headers are right.

Sandbox only. Uses an application token (not the landlord's), since it checks
LedgerLet's behaviour rather than anyone's tax affairs.
"""

from typing import Any, Protocol

import httpx

from app.modules.hmrc.oauth import HmrcAuthError, OAuthClient

ACCEPT = "application/vnd.hmrc.1.0+json"


class FraudHeaderValidator(Protocol):
    def validate(self, headers: dict[str, str]) -> dict[str, Any]: ...


class HttpxFraudHeaderValidator:
    def __init__(self, base_url: str, oauth: OAuthClient) -> None:
        self._url = f"{base_url.rstrip('/')}/test/fraud-prevention-headers/validate"
        self._oauth = oauth

    def validate(self, headers: dict[str, str]) -> dict[str, Any]:
        token = self._oauth.application_token()
        try:
            response = httpx.get(
                self._url,
                headers={**headers, "Authorization": f"Bearer {token}", "Accept": ACCEPT},
                timeout=15.0,
            )
        except httpx.HTTPError as exc:
            raise HmrcAuthError(f"Could not reach HMRC: {exc.__class__.__name__}") from None
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text[:500]}
        return {"http_status": response.status_code, **body}
