"""Give your HMRC sandbox test user a UK property business. Sandbox only.

    python scripts/hmrc_create_property_business.py --sub shaz

Uses the landlord's existing LedgerLet-to-HMRC connection (refreshing the token
if needed) and their saved NINO, then calls HMRC's Self Assessment Test Support
API "Create a Test Business". HMRC deletes sandbox test businesses after 7 days;
just run this again when discovery stops finding it.

Needs: Postgres running, `.env` configured, `.dev-hmrc/device.json` saved, and the
landlord already connected to HMRC with a NINO set.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.database import get_sessionmaker
from app.core.time import uk_today
from app.modules.hmrc.crypto import TokenCipher
from app.modules.hmrc.dependencies import APP_VERSION
from app.modules.hmrc.fraud import (
    ClientDeviceInfo,
    Screen,
    ServerContext,
    VendorInfo,
    build_fraud_headers,
)
from app.modules.hmrc.oauth import HttpxOAuthClient
from app.modules.hmrc.repository import HmrcConnectionRepository, HmrcTaxpayerRepository
from app.modules.hmrc.service import HmrcConnectionService, OAuthSettings
from app.modules.landlords.repository import LandlordRepository
from app.modules.tax.periods import tax_year_containing, tax_year_label

PATH = "/individuals/self-assessment-test-support/business/{nino}"
DEVICE_FILE = Path(".dev-hmrc") / "device.json"


def body_for(tax_year: int) -> dict:
    return {
        "typeOfBusiness": "uk-property",
        "firstAccountingPeriodStartDate": f"{tax_year}-04-06",
        "firstAccountingPeriodEndDate": f"{tax_year + 1}-04-05",
        "quarterlyTypeChoice": {
            "quarterlyPeriodType": "standard",
            "taxYearOfChoice": tax_year_label(tax_year),
        },
        "accountingType": "CASH",
        "commencementDate": "2020-04-06",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--sub", required=True, help="the dev sign-in subject, e.g. shaz")
    args = parser.parse_args()

    s = get_settings()
    if "test-api" not in s.hmrc_base_url:
        sys.exit("Refusing to run: this script is for HMRC's sandbox only.")
    if not (s.auth_issuer and s.hmrc_client_id and s.hmrc_client_secret and s.hmrc_token_key):
        sys.exit("Auth and HMRC settings are missing from .env.")
    if not DEVICE_FILE.exists():
        sys.exit(f"Missing {DEVICE_FILE}. Save it from /api/v1/hmrc/dev/device first.")

    session = get_sessionmaker()()
    try:
        landlord = LandlordRepository(session).find_by_identity(s.auth_issuer, args.sub)
        if landlord is None:
            sys.exit(f"No LedgerLet landlord for --sub {args.sub}. Sign in once via the API.")
        taxpayer = HmrcTaxpayerRepository(session).get_for_landlord(landlord.id)
        if taxpayer is None:
            sys.exit("No NINO saved. PUT /api/v1/hmrc/taxpayer first.")

        cipher = TokenCipher(s.hmrc_token_key)
        connections = HmrcConnectionService(
            HmrcConnectionRepository(session),
            HttpxOAuthClient(
                s.hmrc_base_url, s.hmrc_client_id, s.hmrc_client_secret, s.hmrc_redirect_uri
            ),
            cipher,
            OAuthSettings(
                s.hmrc_authorize_url, s.hmrc_client_id, s.hmrc_redirect_uri, s.hmrc_scopes
            ),
        )
        token = connections.access_token(landlord.id)  # refreshes if needed
        nino = cipher.decrypt(taxpayer.nino_encrypted)
    finally:
        session.close()

    raw = json.loads(DEVICE_FILE.read_text())
    device = ClientDeviceInfo(
        device_id=UUID(raw["device_id"]),
        js_user_agent=raw["js_user_agent"],
        screens=tuple(
            Screen(x["width"], x["height"], x["scaling_factor"], x["colour_depth"])
            for x in raw["screens"]
        ),
        window_width=raw["window_width"],
        window_height=raw["window_height"],
        utc_offset_minutes=raw["utc_offset_minutes"],
    )
    fraud = build_fraud_headers(
        device,
        ServerContext("127.0.0.1", None, datetime.now(UTC), s.hmrc_vendor_public_ip),
        VendorInfo("LedgerLet", {"ledgerlet-api": APP_VERSION}),
        landlord.id,
    )

    tax_year = tax_year_containing(uk_today())
    response = httpx.post(
        f"{s.hmrc_base_url}{PATH.format(nino=nino)}",
        json=body_for(tax_year),
        headers={
            **fraud,
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.hmrc.1.0+json",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    print(f"HMRC returned {response.status_code} for tax year {tax_year_label(tax_year)}")
    print(f"HMRC reference: {response.headers.get('X-CorrelationId')}")
    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text[:500])
    if response.status_code < 300:
        print("\nNow run business discovery again to pick it up.")


if __name__ == "__main__":
    main()
