"""Token verification is the front door, so every way to fake a sign-in is tried here."""

import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.auth import InvalidTokenError, StaticKeySource, TokenVerifier
from tests.auth import AUDIENCE, ISSUER, JWKS, KID, PRIVATE_KEY, make_verifier, mint_token


@pytest.fixture
def verifier():
    return make_verifier()


def test_valid_token_gives_identity(verifier) -> None:
    identity = verifier.verify(mint_token("user-1", email="a@example.com"))
    assert identity.issuer == ISSUER
    assert (identity.subject, identity.email) == ("user-1", "a@example.com")


def test_email_is_optional(verifier) -> None:
    assert verifier.verify(mint_token("user-1")).email is None


def test_email_can_come_from_a_namespaced_claim() -> None:
    """Auth0 adds the email to access tokens only under a namespaced claim name."""
    verifier = TokenVerifier(
        ISSUER, AUDIENCE, StaticKeySource(JWKS), email_claim="https://ledgerlet.app/email"
    )
    token = mint_token("user-1", extra={"https://ledgerlet.app/email": "a@example.com"})
    assert verifier.verify(token).email == "a@example.com"


def test_slight_clock_skew_is_tolerated(verifier) -> None:
    verifier.verify(mint_token("user-1", expires_in=-10))  # expired 10s ago, within 30s leeway


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _hs256_with_public_key() -> str:
    """The classic key-confusion attack: HMAC-sign with the RSA *public* key as the secret."""
    public_pem = PRIVATE_KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": KID}).encode())
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": "attacker", "iat": now, "exp": now + 60}
    payload = _b64(json.dumps(claims).encode())
    signature = hmac.new(public_pem, f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(signature)}"


def _unsigned() -> str:
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": "attacker", "iat": now, "exp": now + 60}
    return jwt.encode(claims, None, algorithm="none", headers={"kid": KID})


OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.mark.parametrize(
    "make_token",
    [
        pytest.param(lambda: mint_token("u", key=OTHER_KEY), id="signed by another key"),
        pytest.param(lambda: mint_token("u", expires_in=-3600), id="expired"),
        pytest.param(lambda: mint_token("u", audience="someone-else"), id="wrong audience"),
        pytest.param(lambda: mint_token("u", issuer="https://evil.example"), id="wrong issuer"),
        pytest.param(lambda: mint_token(None), id="no subject"),
        pytest.param(lambda: mint_token(""), id="empty subject"),
        pytest.param(lambda: mint_token("u", kid="unknown"), id="unknown key id"),
        pytest.param(lambda: mint_token("u", kid=None), id="no key id"),
        pytest.param(_unsigned, id="alg none"),
        pytest.param(_hs256_with_public_key, id="HS256 key confusion"),
        pytest.param(lambda: "not.a.token", id="garbage"),
    ],
)
def test_untrustworthy_tokens_are_rejected(verifier, make_token) -> None:
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token())


def test_static_key_source_round_trips_a_jwks_file(tmp_path) -> None:
    path = tmp_path / "jwks.json"
    path.write_text(json.dumps(JWKS))
    source = StaticKeySource.from_file(path)
    assert source.signing_key(KID) is not None
    with pytest.raises(InvalidTokenError):
        source.signing_key("missing")
