"""HTTP for the HMRC connection.

/connect needs a signed-in landlord. /callback deliberately does not: it's a
browser redirect from HMRC and carries no LedgerLet token. It's trusted through
the sealed state plus the matching cookie instead (see service.py).
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from app.core.config import get_settings
from app.modules.hmrc.dependencies import HmrcServiceDep
from app.modules.hmrc.models import HmrcConnection
from app.modules.hmrc.schemas import ConnectionStatus, ConnectStartRead
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


def _status(connection: HmrcConnection | None) -> ConnectionStatus:
    if connection is None:
        return ConnectionStatus(connected=False)
    return ConnectionStatus(
        connected=True,
        connected_at=connection.connected_at,
        access_token_expires_at=connection.access_token_expires_at,
        scope=connection.scope,
    )
