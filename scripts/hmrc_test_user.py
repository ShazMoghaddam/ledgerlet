"""Create an HMRC sandbox test individual to sign in as. Sandbox only.

    python scripts/hmrc_test_user.py

Uses your Developer Hub credentials from .env to get an application token, then
asks HMRC's Create Test User API for an individual enrolled for MTD Income Tax.
Saves the result to .dev-hmrc/test-user.json (git-ignored) and prints the user
ID and password you'll type into HMRC's sandbox sign-in page.
"""

import json
import sys
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.modules.hmrc.oauth import HmrcAuthError, HttpxOAuthClient

SERVICES = ["national-insurance", "self-assessment", "mtd-income-tax"]
OUT = Path(".dev-hmrc") / "test-user.json"


def main() -> None:
    s = get_settings()
    if "test-api" not in s.hmrc_base_url:
        sys.exit("Refusing to run: this script is for HMRC's sandbox only.")
    if not (s.hmrc_client_id and s.hmrc_client_secret):
        sys.exit("Set LEDGERLET_HMRC_CLIENT_ID and LEDGERLET_HMRC_CLIENT_SECRET in .env first.")

    oauth = HttpxOAuthClient(
        s.hmrc_base_url, s.hmrc_client_id, s.hmrc_client_secret, s.hmrc_redirect_uri
    )
    try:
        token = oauth.application_token()
    except HmrcAuthError as exc:
        sys.exit(f"Could not get an application token: {exc}")

    response = httpx.post(
        f"{s.hmrc_base_url}/create-test-user/individuals",
        json={"serviceNames": SERVICES},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.hmrc.1.0+json",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        sys.exit(f"HMRC returned {response.status_code}: {response.text[:500]}")

    user = response.json()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(user, indent=2))
    OUT.chmod(0o600)
    print(f"Test user saved to {OUT} (git-ignored).")
    print(f"  User ID:  {user.get('userId')}")
    print(f"  Password: {user.get('password')}")
    print(f"  NINO:     {user.get('nino')}")


if __name__ == "__main__":
    main()
