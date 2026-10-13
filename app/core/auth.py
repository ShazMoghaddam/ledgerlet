"""Verifying who a request comes from. Provider-agnostic.

Every mainstream identity provider (Auth0, Clerk, Supabase, Cognito, Entra ID...)
issues signed JWTs and publishes its public keys as a JWKS. LedgerLet only
checks those standard tokens, so changing provider is configuration, not code.

The checks, all of which must pass:
- signed with a key from the provider's key set, using RS256 (never "none" or HS256)
- issued by the configured issuer, for the configured audience
- not expired; has a subject
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol, Self

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings

ALLOWED_ALGORITHMS = ("RS256",)
CLOCK_SKEW_SECONDS = 30


class InvalidTokenError(Exception):
    """The token can't be trusted. The message is for logs, never shown to the caller."""


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str  # the provider's stable user id
    email: str | None


class KeySource(Protocol):
    def signing_key(self, kid: str | None) -> Any: ...


class StaticKeySource:
    """Keys from a JWKS document already in hand (tests, local development)."""

    def __init__(self, jwks: dict[str, Any]) -> None:
        self._keys = {k.key_id: k.key for k in jwt.PyJWKSet.from_dict(jwks).keys}

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        return cls(json.loads(Path(path).read_text()))

    def signing_key(self, kid: str | None) -> Any:
        if kid not in self._keys:
            raise InvalidTokenError(f"Unknown signing key id {kid!r}")
        return self._keys[kid]


class JwksUrlKeySource:
    """Keys fetched from the provider's JWKS URL, cached, refreshed when a new key id appears."""

    def __init__(self, url: str) -> None:
        self._client = jwt.PyJWKClient(url, cache_keys=True)

    def signing_key(self, kid: str | None) -> Any:
        if kid is None:
            raise InvalidTokenError("Token has no key id")
        try:
            return self._client.get_signing_key(kid).key
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from None


class TokenVerifier:
    def __init__(
        self, issuer: str, audience: str, key_source: KeySource, email_claim: str = "email"
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._keys = key_source
        self._email_claim = email_claim

    def verify(self, token: str) -> VerifiedIdentity:
        try:
            header = jwt.get_unverified_header(token)
            key = self._keys.signing_key(header.get("kid"))
            claims = jwt.decode(
                token,
                key,
                algorithms=list(ALLOWED_ALGORITHMS),
                audience=self._audience,
                issuer=self._issuer,
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from None

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise InvalidTokenError("Token subject is empty")
        email = claims.get(self._email_claim)
        return VerifiedIdentity(
            issuer=self._issuer,
            subject=subject,
            email=email if isinstance(email, str) else None,
        )


@lru_cache
def get_token_verifier() -> TokenVerifier:
    """FastAPI dependency. Built once from settings; tests override it."""
    settings = get_settings()
    if not settings.auth_issuer or not (settings.auth_jwks_url or settings.auth_jwks_file):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    source: KeySource = (
        JwksUrlKeySource(settings.auth_jwks_url)
        if settings.auth_jwks_url
        else StaticKeySource.from_file(settings.auth_jwks_file or "")
    )
    return TokenVerifier(
        settings.auth_issuer, settings.auth_audience, source, settings.auth_email_claim
    )
