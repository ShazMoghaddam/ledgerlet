"""HMRC's OAuth 2.0 token endpoint. The only file here that makes HTTP calls.

Grants used:
- authorization_code: a landlord has approved LedgerLet; swap the code for tokens
- refresh_token: the 4-hour access token is near expiry; get a new pair
- client_credentials: an application-level token, for sandbox tools such as
  Create Test User (not tied to any landlord)
"""

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

TIMEOUT_SECONDS = 15.0


class HmrcAuthError(Exception):
    """HMRC refused: bad or reused code, revoked grant, wrong credentials."""


@dataclass(frozen=True)
class TokenGrant:
    access_token: str
    refresh_token: str
    expires_in: int  # seconds
    scope: str


class OAuthClient(Protocol):
    def exchange_code(self, code: str) -> TokenGrant: ...
    def refresh(self, refresh_token: str) -> TokenGrant: ...
    def application_token(self) -> str: ...


class HttpxOAuthClient:
    def __init__(
        self, base_url: str, client_id: str, client_secret: str, redirect_uri: str
    ) -> None:
        self._token_url = f"{base_url.rstrip('/')}/oauth/token"
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def exchange_code(self, code: str) -> TokenGrant:
        return self._grant(
            {"grant_type": "authorization_code", "code": code, "redirect_uri": self._redirect_uri}
        )

    def refresh(self, refresh_token: str) -> TokenGrant:
        return self._grant({"grant_type": "refresh_token", "refresh_token": refresh_token})

    def application_token(self) -> str:
        return str(self._post({"grant_type": "client_credentials"})["access_token"])

    def _grant(self, form: dict[str, str]) -> TokenGrant:
        body = self._post(form)
        try:
            return TokenGrant(
                access_token=body["access_token"],
                refresh_token=body["refresh_token"],
                expires_in=int(body["expires_in"]),
                scope=str(body.get("scope", "")),
            )
        except (KeyError, TypeError, ValueError):
            raise HmrcAuthError("HMRC token response was missing fields") from None

    def _post(self, form: dict[str, str]) -> dict[str, Any]:
        form = {**form, "client_id": self._client_id, "client_secret": self._client_secret}
        try:
            response = httpx.post(self._token_url, data=form, timeout=TIMEOUT_SECONDS)
        except httpx.HTTPError as exc:
            raise HmrcAuthError(f"Could not reach HMRC: {exc.__class__.__name__}") from None
        if response.status_code >= 400:
            # HMRC's error body names the problem (e.g. invalid_grant) and holds no secrets.
            raise HmrcAuthError(f"HMRC returned {response.status_code}: {response.text[:300]}")
        return response.json()
