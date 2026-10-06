"""Ask HMRC's sandbox for obligations several ways at once, to see which it answers. Read-only.

    python scripts/hmrc_probe_obligations.py --sub shaz

Same setup as hmrc_create_property_business.py (Postgres up, connected, NINO and
business chosen, .dev-hmrc/device.json saved). Prints one line per variant.
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
from app.modules.hmrc import api
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

DEVICE_FILE = Path(".dev-hmrc") / "device.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sub", required=True)
    args = parser.parse_args()
    s = get_settings()
    if "test-api" not in s.hmrc_base_url:
        sys.exit("Sandbox only.")

    session = get_sessionmaker()()
    try:
        landlord = LandlordRepository(session).find_by_identity(s.auth_issuer or "", args.sub)
        if landlord is None:
            sys.exit("No landlord for that --sub.")
        taxpayer = HmrcTaxpayerRepository(session).get_for_landlord(landlord.id)
        if taxpayer is None or not taxpayer.uk_property_business_id:
            sys.exit("Save a NINO and discover the business first.")
        cipher = TokenCipher(s.hmrc_token_key or "")
        token = HmrcConnectionService(
            HmrcConnectionRepository(session),
            HttpxOAuthClient(
                s.hmrc_base_url, s.hmrc_client_id or "", s.hmrc_client_secret or "",
                s.hmrc_redirect_uri,
            ),
            cipher,
            OAuthSettings(
                s.hmrc_authorize_url, s.hmrc_client_id or "", s.hmrc_redirect_uri, s.hmrc_scopes
            ),
        ).access_token(landlord.id)
        nino = cipher.decrypt(taxpayer.nino_encrypted)
        business_id = taxpayer.uk_property_business_id
    finally:
        session.close()

    raw = json.loads(DEVICE_FILE.read_text())
    fraud = build_fraud_headers(
        ClientDeviceInfo(
            UUID(raw["device_id"]),
            raw["js_user_agent"],
            tuple(Screen(x["width"], x["height"], x["scaling_factor"], x["colour_depth"])
                  for x in raw["screens"]),
            raw["window_width"],
            raw["window_height"],
            raw["utc_offset_minutes"],
        ),
        ServerContext("127.0.0.1", None, datetime.now(UTC), s.hmrc_vendor_public_ip),
        VendorInfo("LedgerLet", {"ledgerlet-api": APP_VERSION}),
        landlord.id,
    )
    url = f"{s.hmrc_base_url}{api.OBLIGATIONS.format(nino=nino)}"
    business = {"typeOfBusiness": "uk-property", "businessId": business_id}
    dates = {"fromDate": "2026-04-06", "toDate": "2027-04-05"}

    variants = [
        ("no scenario, business+dates", None, {**business, **dates}),
        ("DYNAMIC, business+dates", "DYNAMIC", {**business, **dates}),
        ("DYNAMIC, business only", "DYNAMIC", business),
        ("DYNAMIC, no filters", "DYNAMIC", {}),
        ("DYNAMIC, status=open", "DYNAMIC", {"status": "open"}),
        ("no scenario, no filters", None, {}),
    ]
    for label, scenario, params in variants:
        headers = {
            **fraud,
            "Authorization": f"Bearer {token}",
            "Accept": f"application/vnd.hmrc.{api.OBLIGATIONS_VERSION}+json",
        }
        if scenario:
            headers["Gov-Test-Scenario"] = scenario
        r = httpx.get(url, headers=headers, params=params, timeout=20)
        try:
            body = r.json()
        except ValueError:
            body = {}
        details = [
            d for g in body.get("obligations", []) for d in g.get("obligationDetails", [])
        ]
        summary = body.get("code") or f"{len(details)} obligation(s)"
        print(f"{label:30} -> {r.status_code} {summary}")
        for d in details[:6]:
            print(
                f"{'':33}{d.get('periodStartDate')} to {d.get('periodEndDate')}"
                f"  due {d.get('dueDate')}  {d.get('status')}"
                f"  [{d.get('businessId', '')}]"
            )
        if details:
            groups = [(g.get("typeOfBusiness"), g.get("businessId")) for g in body["obligations"]]
            print(f"{'':33}groups: {groups}")


if __name__ == "__main__":
    main()
