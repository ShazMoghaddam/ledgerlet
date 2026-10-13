"""Test identity provider: a throwaway RSA key that signs tokens like a real provider.

API tests call headers(landlord_id) to get a valid bearer token whose subject is
that id. Each distinct id is a distinct landlord, created on first request.
"""

import json
import time
from typing import Any
from uuid import UUID

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.core.auth import StaticKeySource, TokenVerifier

ISSUER = "https://auth.test.ledgerlet"
AUDIENCE = "ledgerlet-api"
KID = "test-key-1"

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_jwk = json.loads(RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key()))
_jwk.update(kid=KID, use="sig", alg="RS256")
JWKS: dict[str, Any] = {"keys": [_jwk]}


def make_verifier() -> TokenVerifier:
    return TokenVerifier(ISSUER, AUDIENCE, StaticKeySource(JWKS))


def mint_token(
    subject: str | None,
    *,
    email: str | None = None,
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
    expires_in: int = 3600,
    key: Any = PRIVATE_KEY,
    kid: str | None = KID,
    extra: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {"iss": issuer, "aud": audience, "iat": now, "exp": now + expires_in}
    if subject is not None:
        claims["sub"] = subject
    if email is not None:
        claims["email"] = email
    claims.update(extra or {})
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid} if kid else None)


def headers(landlord_id: UUID | str, email: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_token(str(landlord_id), email=email)}"}
