"""Fraud prevention headers: each format pinned, since HMRC rejects near-misses."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.modules.hmrc.fraud import (
    CONNECTION_METHOD,
    ClientDeviceInfo,
    Screen,
    ServerContext,
    VendorInfo,
    build_fraud_headers,
    format_screens,
    format_timestamp,
    format_timezone,
)

LANDLORD = UUID("379eff6e-e5d9-44c9-a5d8-c75369dd9e4e")
DEVICE = ClientDeviceInfo(
    device_id=UUID("beec798b-b366-47fa-b1f8-92cead59b56e"),
    js_user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    screens=(Screen(1512, 982, 2, 30),),
    window_width=1512,
    window_height=860,
    utc_offset_minutes=60,
)
SERVER = ServerContext(
    client_public_ip="203.0.113.6",
    client_public_port=51234,
    client_ip_seen_at=datetime(2026, 10, 5, 14, 0, tzinfo=UTC),
    vendor_public_ip="198.51.100.1",
)
VENDOR = VendorInfo(product_name="LedgerLet", versions={"ledgerlet-api": "0.1.0"})


@pytest.mark.parametrize(
    ("offset", "expected"),
    [(60, "UTC+01:00"), (0, "UTC+00:00"), (-330, "UTC-05:30"), (345, "UTC+05:45")],
)
def test_timezone(offset: int, expected: str) -> None:
    assert format_timezone(offset) == expected


def test_timestamp_is_utc_with_milliseconds() -> None:
    bst = timezone(timedelta(hours=1))
    assert format_timestamp(datetime(2026, 10, 5, 15, 49, 57, 37375, tzinfo=bst)) == (
        "2026-10-05T14:49:57.037Z"
    )


def test_multiple_screens() -> None:
    assert format_screens((Screen(1920, 1080, 2, 30), Screen(1280, 720, 1.25, 24))) == (
        "width=1920&height=1080&scaling-factor=2&colour-depth=30,"
        "width=1280&height=720&scaling-factor=1.25&colour-depth=24"
    )


def test_full_header_set() -> None:
    h = build_fraud_headers(DEVICE, SERVER, VENDOR, LANDLORD)
    assert h["Gov-Client-Connection-Method"] == CONNECTION_METHOD == "WEB_APP_VIA_SERVER"
    assert h["Gov-Client-Device-ID"] == "beec798b-b366-47fa-b1f8-92cead59b56e"
    assert h["Gov-Client-Public-IP"] == "203.0.113.6"
    assert h["Gov-Client-Public-Port"] == "51234"
    assert h["Gov-Client-Public-IP-Timestamp"] == "2026-10-05T14:00:00.000Z"
    assert h["Gov-Client-Timezone"] == "UTC+01:00"
    assert h["Gov-Client-User-IDs"] == f"ledgerlet={LANDLORD}"
    assert h["Gov-Client-Window-Size"] == "width=1512&height=860"
    assert h["Gov-Vendor-Version"] == "ledgerlet-api=0.1.0"
    assert h["Gov-Vendor-Public-IP"] == "198.51.100.1"
    assert h["Gov-Vendor-Forwarded"] == "by=198.51.100.1&for=203.0.113.6"


def test_values_inside_structures_are_percent_encoded() -> None:
    vendor = VendorInfo(product_name="LedgerLet & Co", versions={"ledger let": "1.0=b"})
    h = build_fraud_headers(DEVICE, SERVER, vendor, LANDLORD)
    assert h["Gov-Vendor-Product-Name"] == "LedgerLet%20%26%20Co"
    assert h["Gov-Vendor-Version"] == "ledger%20let=1.0%3Db"


def test_headers_we_cannot_fill_are_left_out_not_faked() -> None:
    local = ServerContext("127.0.0.1", None, SERVER.client_ip_seen_at, None)
    h = build_fraud_headers(DEVICE, local, VENDOR, LANDLORD)
    for name in (
        "Gov-Client-Public-Port",
        "Gov-Vendor-Public-IP",
        "Gov-Vendor-Forwarded",
        "Gov-Vendor-License-IDs",
    ):
        assert name not in h
