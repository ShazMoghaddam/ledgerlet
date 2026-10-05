"""HMRC fraud prevention headers, for the WEB_APP_VIA_SERVER connection method.

HMRC requires every MTD API call to describe the user's device and the route
the request took. Some facts come from the user's browser (screen, window,
browser, timezone, a persistent device id); the rest are known only to our
server (the user's public IP and port, our own public IP, our version).

Pure functions only: no HTTP, no database. HMRC's Test Fraud Prevention
Headers API is the judge of whether the result is right, so each header is a
small separately tested formatter that's easy to adjust when HMRC says so.

Encoding: within structured values, keys and values are percent-encoded.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID

CONNECTION_METHOD = "WEB_APP_VIA_SERVER"


@dataclass(frozen=True)
class Screen:
    width: int
    height: int
    scaling_factor: float
    colour_depth: int


@dataclass(frozen=True)
class ClientDeviceInfo:
    """Collected in the user's browser and sent with each request."""

    device_id: UUID  # generated once, kept in the browser's local storage
    js_user_agent: str  # navigator.userAgent
    screens: tuple[Screen, ...]
    window_width: int
    window_height: int
    utc_offset_minutes: int  # e.g. 60 during British Summer Time


@dataclass(frozen=True)
class ServerContext:
    """What our server knows about this request."""

    client_public_ip: str
    client_public_port: int | None
    client_ip_seen_at: datetime
    vendor_public_ip: str | None  # our server's public IP, if known


@dataclass(frozen=True)
class VendorInfo:
    product_name: str
    versions: dict[str, str]  # software name -> version
    license_ids: dict[str, str] = field(default_factory=dict)


def _enc(value: object) -> str:
    return quote(str(value), safe="")


def _pairs(items: dict[str, object]) -> str:
    return "&".join(f"{_enc(k)}={_enc(v)}" for k, v in items.items())


def format_timezone(utc_offset_minutes: int) -> str:
    """60 -> 'UTC+01:00', -330 -> 'UTC-05:30', 0 -> 'UTC+00:00'."""
    sign = "+" if utc_offset_minutes >= 0 else "-"
    hours, minutes = divmod(abs(utc_offset_minutes), 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def format_timestamp(moment: datetime) -> str:
    """UTC with milliseconds: 2026-10-05T14:49:57.037Z."""
    utc = moment.astimezone(UTC)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{utc.microsecond // 1000:03d}Z"


def format_screens(screens: tuple[Screen, ...]) -> str:
    return ",".join(
        _pairs(
            {
                "width": s.width,
                "height": s.height,
                "scaling-factor": f"{s.scaling_factor:g}",
                "colour-depth": s.colour_depth,
            }
        )
        for s in screens
    )


def build_fraud_headers(
    device: ClientDeviceInfo,
    server: ServerContext,
    vendor: VendorInfo,
    landlord_id: UUID,
) -> dict[str, str]:
    headers = {
        "Gov-Client-Connection-Method": CONNECTION_METHOD,
        "Gov-Client-Browser-JS-User-Agent": device.js_user_agent,
        "Gov-Client-Device-ID": str(device.device_id),
        "Gov-Client-Public-IP": server.client_public_ip,
        "Gov-Client-Public-IP-Timestamp": format_timestamp(server.client_ip_seen_at),
        "Gov-Client-Screens": format_screens(device.screens),
        "Gov-Client-Timezone": format_timezone(device.utc_offset_minutes),
        "Gov-Client-User-IDs": _pairs({"ledgerlet": landlord_id}),
        "Gov-Client-Window-Size": _pairs(
            {"width": device.window_width, "height": device.window_height}
        ),
        "Gov-Vendor-Product-Name": _enc(vendor.product_name),
        "Gov-Vendor-Version": _pairs(dict(vendor.versions)),
    }
    if server.client_public_port is not None:
        headers["Gov-Client-Public-Port"] = str(server.client_public_port)
    if server.vendor_public_ip:
        headers["Gov-Vendor-Public-IP"] = server.vendor_public_ip
        headers["Gov-Vendor-Forwarded"] = _pairs(
            {"by": server.vendor_public_ip, "for": server.client_public_ip}
        )
    if vendor.license_ids:
        headers["Gov-Vendor-License-IDs"] = _pairs(dict(vendor.license_ids))
    return headers
