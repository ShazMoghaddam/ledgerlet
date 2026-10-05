"""HTTP for the HMRC connection.

/connect needs a signed-in landlord. /callback deliberately does not: it's a
browser redirect from HMRC and carries no LedgerLet token. It's trusted through
the sealed state plus the matching cookie instead (see service.py).
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from fastapi.responses import HTMLResponse

from app.core.config import get_settings
from app.modules.hmrc.dependencies import (
    ClientDeviceDep,
    FraudValidatorDep,
    HmrcServiceDep,
    ServerContextDep,
    VendorInfoDep,
)
from app.modules.hmrc.fraud import build_fraud_headers
from app.modules.hmrc.models import HmrcConnection
from app.modules.hmrc.schemas import ConnectionStatus, ConnectStartRead, FraudHeaderCheck
from app.modules.hmrc.service import STATE_MAX_AGE_SECONDS, HmrcConnectError
from app.modules.landlords.dependencies import CurrentLandlordId

router = APIRouter(prefix="/hmrc", tags=["hmrc"])

STATE_COOKIE = "ledgerlet_hmrc_connect"
COOKIE_PATH = "/api/v1/hmrc"


@router.post("/connect", response_model=ConnectStartRead)
def start_connect(landlord_id: CurrentLandlordId, service: HmrcServiceDep, response: Response):
    start = service.start(landlord_id)
    response.set_cookie(
        STATE_COOKIE,
        start.nonce,
        max_age=STATE_MAX_AGE_SECONDS,
        path=COOKIE_PATH,
        httponly=True,  # page scripts can't read it
        samesite="lax",  # sent on HMRC's top-level redirect back, not on cross-site requests
        secure=get_settings().environment == "production",
    )
    return ConnectStartRead(authorize_url=start.authorize_url)


@router.get("/callback", response_model=ConnectionStatus)
def callback(
    service: HmrcServiceDep,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    nonce: Annotated[str | None, Cookie(alias=STATE_COOKIE)] = None,
):
    if error:
        raise HmrcConnectError(f"HMRC approval was not completed ({error})")
    if not code or not state:
        raise HmrcConnectError("HMRC did not send back an approval code")
    connection = service.complete(code, state, nonce)
    response.delete_cookie(STATE_COOKIE, path=COOKIE_PATH)
    return _status(connection)


@router.get("/connection", response_model=ConnectionStatus)
def get_connection(landlord_id: CurrentLandlordId, service: HmrcServiceDep):
    return _status(service.status(landlord_id))


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(landlord_id: CurrentLandlordId, service: HmrcServiceDep) -> None:
    service.disconnect(landlord_id)


@router.post("/fraud-headers/validate", response_model=FraudHeaderCheck)
def validate_fraud_headers(
    landlord_id: CurrentLandlordId,
    device: ClientDeviceDep,
    server: ServerContextDep,
    vendor: VendorInfoDep,
    validator: FraudValidatorDep,
):
    """Build this request's fraud prevention headers and ask HMRC's sandbox to check them."""
    headers = build_fraud_headers(device, server, vendor, landlord_id)
    return FraudHeaderCheck(headers_sent=headers, hmrc_response=validator.validate(headers))


@router.get("/dev/device", response_class=HTMLResponse, include_in_schema=False)
def device_probe() -> str:
    """Development only: shows the device JSON this browser would send.

    A real frontend will gather the same facts in the same way.
    """
    if get_settings().environment == "production":
        raise HTTPException(status_code=404)
    return DEVICE_PROBE_HTML


DEVICE_PROBE_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>LedgerLet device details</title>
<style>body{font:15px system-ui;margin:2rem;max-width:60rem}
pre{background:#f3f3f3;padding:1rem;white-space:pre-wrap;word-break:break-all}</style></head>
<body><h1>Device details for HMRC</h1>
<p>Copy this into the <code>X-LedgerLet-Device</code> header in Swagger.
The device id is kept in this browser, so it stays the same next time.</p>
<pre id="out"></pre><button onclick="navigator.clipboard.writeText(out.textContent)">Copy</button>
<script>
let id = localStorage.getItem("ledgerlet-device-id");
if (!id) { id = crypto.randomUUID(); localStorage.setItem("ledgerlet-device-id", id); }
const device = {
  device_id: id,
  js_user_agent: navigator.userAgent,
  screens: [{width: screen.width, height: screen.height,
             scaling_factor: window.devicePixelRatio, colour_depth: screen.colorDepth}],
  window_width: window.innerWidth,
  window_height: window.innerHeight,
  utc_offset_minutes: -new Date().getTimezoneOffset()
};
document.getElementById("out").textContent = JSON.stringify(device);
</script></body></html>"""


def _status(connection: HmrcConnection | None) -> ConnectionStatus:
    if connection is None:
        return ConnectionStatus(connected=False)
    return ConnectionStatus(
        connected=True,
        connected_at=connection.connected_at,
        access_token_expires_at=connection.access_token_expires_at,
        scope=connection.scope,
    )
