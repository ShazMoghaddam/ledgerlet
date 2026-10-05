"""A stand-in identity provider for local development. Never used in production.

    python scripts/dev_auth.py init
        Creates a signing key in .dev-auth/ (git-ignored) and prints the
        settings to put in your .env.

    python scripts/dev_auth.py token --sub alice --email alice@example.com
        Prints a sign-in token (valid 8 hours) for that user. Paste it into
        the Authorize button on /docs.

It signs tokens exactly the way a real provider does (RS256, kid, iss, aud,
exp), so the API code path is identical to production.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

DIR = Path(".dev-auth")
PRIVATE_KEY = DIR / "private.pem"
JWKS_FILE = DIR / "jwks.json"
ISSUER = "http://localhost/dev-auth"
AUDIENCE = "ledgerlet-api"
KID = "dev-key-1"


def init() -> None:
    DIR.mkdir(exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    PRIVATE_KEY.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    PRIVATE_KEY.chmod(0o600)
    jwk = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid=KID, use="sig", alg="RS256")
    JWKS_FILE.write_text(json.dumps({"keys": [jwk]}, indent=2))
    print("Dev signing key created in .dev-auth/ (git-ignored). Add these to .env:\n")
    print(f"LEDGERLET_AUTH_ISSUER={ISSUER}")
    print(f"LEDGERLET_AUTH_AUDIENCE={AUDIENCE}")
    print(f"LEDGERLET_AUTH_JWKS_FILE={JWKS_FILE}")


def token(subject: str, email: str | None, hours: float) -> None:
    if not PRIVATE_KEY.exists():
        sys.exit("No dev key yet. Run: python scripts/dev_auth.py init")
    key = serialization.load_pem_private_key(PRIVATE_KEY.read_bytes(), password=None)
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": subject, "iat": now}
    claims["exp"] = now + int(hours * 3600)
    if email:
        claims["email"] = email
    print(jwt.encode(claims, key, algorithm="RS256", headers={"kid": KID}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create a dev signing key")
    tok = sub.add_parser("token", help="print a sign-in token")
    tok.add_argument("--sub", required=True, help="user id, e.g. alice")
    tok.add_argument("--email")
    tok.add_argument("--hours", type=float, default=8)
    args = parser.parse_args()
    if args.command == "init":
        init()
    else:
        token(args.sub, args.email, args.hours)


if __name__ == "__main__":
    main()
