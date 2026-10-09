"""HTTP for the HMRC connection.

/connect needs a signed-in landlord. /callback deliberately does not: it's a
browser redirect from HMRC and carries no LedgerLet token. It's trusted through
the sealed state plus the matching cookie instead (see service.py).

/callback always ends by sending the browser back into the web app: to the
page the landlord started from with ?hmrc=connected, or to the HMRC settings
page with ?hmrc=error&reason=<code>.
"""

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import get_settings
from app.core.time import uk_today, utc_now
from app.modules.hmrc.dependencies import (
    ClientDeviceDep,
    FraudHeadersDep,
    FraudValidatorDep,
    HmrcServiceDep,
    ServerContextDep,
    SubmissionServiceDep,
    TaxpayerServiceDep,
    VendorInfoDep,
)
from app.modules.hmrc.fraud import build_fraud_headers
from app.modules.hmrc.models import HmrcConnection, HmrcTaxpayer
from app.modules.hmrc.schemas import (
    BusinessIdIn,
    BusinessRead,
    ConnectionStatus,
    ConnectStartIn,
    ConnectStartRead,
    DiscoveryRead,
    FraudHeaderCheck,
    HmrcObligationRead,
    HmrcObligationsRead,
    NinoIn,
    SubmissionPreviewRead,
    SubmissionRead,
    SubmissionRequest,
    TaxpayerRead,
)
from app.modules.hmrc.service import (
    DEFAULT_RETURN_TO,
    STATE_MAX_AGE_SECONDS,
    HmrcConnectError,
)
from app.modules.landlords.dependencies import CurrentLandlord, CurrentLandlordId
from app.modules.tax.periods import (
    PeriodBasis,
    tax_year_containing,
    tax_year_label,
    update_period,
)

router = APIRouter(prefix="/hmrc", tags=["hmrc"])

STATE_COOKIE = "ledgerlet_hmrc_connect"
COOKIE_PATH = "/api/v1/hmrc"


@router.post("/connect", response_model=ConnectStartRead)
def start_connect(
    landlord_id: CurrentLandlordId,
    service: HmrcServiceDep,
    response: Response,
    payload: ConnectStartIn | None = None,
):
    start = service.start(landlord_id, (payload or ConnectStartIn()).return_to)
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


@router.get("/callback", response_class=RedirectResponse, status_code=303)
def callback(
    service: HmrcServiceDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    nonce: Annotated[str | None, Cookie(alias=STATE_COOKIE)] = None,
) -> RedirectResponse:
    try:
        if error:
            # "access_denied" means the landlord chose not to approve at HMRC.
            reason = "declined" if error == "access_denied" else "failed"
            raise HmrcConnectError(f"HMRC approval was not completed ({error})", reason)
        if not code or not state:
            raise HmrcConnectError("HMRC did not send back an approval code", "invalid")
        done = service.complete(code, state, nonce)
        redirect = _back_to_app(done.return_to, {"hmrc": "connected"})
    except HmrcConnectError as exc:
        redirect = _back_to_app(DEFAULT_RETURN_TO, {"hmrc": "error", "reason": exc.reason})
    redirect.delete_cookie(STATE_COOKIE, path=COOKIE_PATH)  # one attempt per start
    return redirect


def _back_to_app(path: str, params: dict[str, str]) -> RedirectResponse:
    """path is trusted: it was checked on the way in and sealed inside the state."""
    joiner = "&" if "?" in path else "?"
    url = f"{get_settings().app_base_url.rstrip('/')}{path}{joiner}{urlencode(params)}"
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


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


@router.get("/taxpayer", response_model=TaxpayerRead)
def get_taxpayer(landlord_id: CurrentLandlordId, service: TaxpayerServiceDep):
    return _taxpayer(service, service.profile(landlord_id))


@router.put("/taxpayer", response_model=TaxpayerRead)
def set_nino(payload: NinoIn, landlord_id: CurrentLandlordId, service: TaxpayerServiceDep):
    return _taxpayer(service, service.set_nino(landlord_id, payload.nino))


@router.put("/taxpayer/business", response_model=TaxpayerRead)
def set_business(
    payload: BusinessIdIn, landlord_id: CurrentLandlordId, service: TaxpayerServiceDep
):
    return _taxpayer(service, service.set_business(landlord_id, payload.business_id))


@router.post("/businesses/discover", response_model=DiscoveryRead)
def discover_businesses(
    landlord_id: CurrentLandlordId, fraud_headers: FraudHeadersDep, service: TaxpayerServiceDep
):
    """Ask HMRC which businesses this landlord has; auto-select a single UK property one."""
    businesses, taxpayer = service.discover_businesses(landlord_id, fraud_headers)
    return DiscoveryRead(
        businesses=[
            BusinessRead(
                business_id=b.business_id,
                type_of_business=b.type_of_business,
                trading_name=b.trading_name,
            )
            for b in businesses
        ],
        selected_business_id=taxpayer.uk_property_business_id,
    )


@router.get("/obligations", response_model=HmrcObligationsRead)
def get_obligations(
    landlord_id: CurrentLandlordId,
    fraud_headers: FraudHeadersDep,
    service: TaxpayerServiceDep,
    tax_year: int | None = None,
):
    """HMRC's own list of quarterly updates due for this landlord's UK property business."""
    year = tax_year if tax_year is not None else tax_year_containing(utc_now().date())
    whole_year = update_period(year, 4, PeriodBasis.STANDARD)
    found, raw = service.obligations(landlord_id, fraud_headers, whole_year.start, whole_year.end)
    return HmrcObligationsRead(
        obligations=[
            HmrcObligationRead(
                period_start=o.period_start,
                period_end=o.period_end,
                due=o.due,
                status=o.status,
                received=o.received,
            )
            for o in found
        ],
        hmrc_response=raw,
    )


@router.post("/submissions/preview", response_model=SubmissionPreviewRead)
def preview_submission(
    payload: SubmissionRequest, landlord: CurrentLandlord, service: SubmissionServiceDep
):
    """Exactly what would be sent to HMRC for this quarter. Sends nothing."""
    year = _year(payload.tax_year)
    p = service.preview(
        landlord.id,
        year,
        payload.quarter,
        payload.basis or landlord.period_basis,
        payload.consolidated_expenses,
    )
    return SubmissionPreviewRead(
        tax_year_label=tax_year_label(year),
        quarter=p.period.quarter,
        period_start=p.period.start,
        period_end=p.period.end,
        body=p.body,
    )


@router.post("/submissions", response_model=SubmissionRead, status_code=201)
def submit_update(
    payload: SubmissionRequest,
    landlord: CurrentLandlord,
    fraud_headers: FraudHeadersDep,
    service: SubmissionServiceDep,
):
    """Send the cumulative quarterly update to HMRC. Every attempt is recorded."""
    return service.submit(
        landlord.id,
        _year(payload.tax_year),
        payload.quarter,
        payload.basis or landlord.period_basis,
        payload.consolidated_expenses,
        fraud_headers,
    )


@router.get("/submissions", response_model=list[SubmissionRead])
def list_submissions(
    landlord_id: CurrentLandlordId, service: SubmissionServiceDep, tax_year: int | None = None
):
    return service.history(landlord_id, tax_year)


def _year(tax_year: int | None) -> int:
    return tax_year if tax_year is not None else tax_year_containing(uk_today())


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


def _taxpayer(service, taxpayer: HmrcTaxpayer | None) -> TaxpayerRead:
    if taxpayer is None:
        return TaxpayerRead(nino=None, uk_property_business_id=None)
    return TaxpayerRead(
        nino=service.masked_nino(taxpayer),
        uk_property_business_id=taxpayer.uk_property_business_id,
    )


def _status(connection: HmrcConnection | None) -> ConnectionStatus:
    if connection is None:
        return ConnectionStatus(connected=False)
    return ConnectionStatus(
        connected=True,
        connected_at=connection.connected_at,
        access_token_expires_at=connection.access_token_expires_at,
        scope=connection.scope,
    )
