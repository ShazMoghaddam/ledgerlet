"""Wiring for the HMRC module. Tests override the cipher, OAuth client and validator."""

import json
from datetime import datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.time import utc_now
from app.modules.hmrc.api import HmrcApi, HttpxHmrcApi
from app.modules.hmrc.crypto import TokenCipher
from app.modules.hmrc.fraud import (
    ClientDeviceInfo,
    Screen,
    ServerContext,
    VendorInfo,
    build_fraud_headers,
)
from app.modules.hmrc.oauth import HttpxOAuthClient, OAuthClient
from app.modules.hmrc.repository import HmrcConnectionRepository, HmrcTaxpayerRepository
from app.modules.hmrc.schemas import ClientDevice
from app.modules.hmrc.service import HmrcConnectionService, OAuthSettings
from app.modules.hmrc.taxpayer import HmrcTaxpayerService
from app.modules.hmrc.validator import FraudHeaderValidator, HttpxFraudHeaderValidator
from app.modules.landlords.dependencies import CurrentLandlordId

_NOT_CONFIGURED = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="The HMRC connection is not configured",
)


@lru_cache
def get_token_cipher() -> TokenCipher:
    key = get_settings().hmrc_token_key
    if not key:
        raise _NOT_CONFIGURED
    return TokenCipher(key)


@lru_cache
def get_oauth_client() -> OAuthClient:
    s = get_settings()
    if not (s.hmrc_client_id and s.hmrc_client_secret):
        raise _NOT_CONFIGURED
    return HttpxOAuthClient(
        s.hmrc_base_url, s.hmrc_client_id, s.hmrc_client_secret, s.hmrc_redirect_uri
    )


def get_oauth_settings() -> OAuthSettings:
    s = get_settings()
    if not s.hmrc_client_id:
        raise _NOT_CONFIGURED
    return OAuthSettings(
        authorize_url=s.hmrc_authorize_url,
        client_id=s.hmrc_client_id,
        redirect_uri=s.hmrc_redirect_uri,
        scopes=s.hmrc_scopes,
    )


def get_hmrc_service(
    db: Annotated[Session, Depends(get_db)],
    cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
    oauth: Annotated[OAuthClient, Depends(get_oauth_client)],
    settings: Annotated[OAuthSettings, Depends(get_oauth_settings)],
) -> HmrcConnectionService:
    return HmrcConnectionService(HmrcConnectionRepository(db), oauth, cipher, settings)


HmrcServiceDep = Annotated[HmrcConnectionService, Depends(get_hmrc_service)]


# Fraud prevention: device facts from the browser, request facts from the server.

DEVICE_HEADER = "X-LedgerLet-Device"
APP_VERSION = "0.1.0"


def get_client_device(
    x_ledgerlet_device: Annotated[str | None, Header()] = None,
) -> ClientDeviceInfo:
    if not x_ledgerlet_device:
        raise HTTPException(
            status_code=422,
            detail=f"Send the browser's device details in the {DEVICE_HEADER} header",
        )
    try:
        device = ClientDevice.model_validate(json.loads(x_ledgerlet_device))
    except (ValueError, ValidationError):
        raise HTTPException(
            status_code=422, detail=f"The {DEVICE_HEADER} header is not valid device JSON"
        ) from None
    return ClientDeviceInfo(
        device_id=device.device_id,
        js_user_agent=device.js_user_agent,
        screens=tuple(
            Screen(s.width, s.height, s.scaling_factor, s.colour_depth) for s in device.screens
        ),
        window_width=device.window_width,
        window_height=device.window_height,
        utc_offset_minutes=device.utc_offset_minutes,
    )


def get_server_context(request: Request) -> ServerContext:
    settings = get_settings()
    ip = request.client.host if request.client else "0.0.0.0"
    port = request.client.port if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if settings.trust_proxy_headers and forwarded:
        ip = forwarded.split(",")[0].strip()  # the original client, as our own proxy saw it
    seen_at: datetime = utc_now()
    return ServerContext(
        client_public_ip=ip,
        client_public_port=port,
        client_ip_seen_at=seen_at,
        vendor_public_ip=settings.hmrc_vendor_public_ip,
    )


def get_vendor_info() -> VendorInfo:
    return VendorInfo(product_name="LedgerLet", versions={"ledgerlet-api": APP_VERSION})


@lru_cache
def get_fraud_validator() -> FraudHeaderValidator:
    return HttpxFraudHeaderValidator(get_settings().hmrc_base_url, get_oauth_client())


ClientDeviceDep = Annotated[ClientDeviceInfo, Depends(get_client_device)]
ServerContextDep = Annotated[ServerContext, Depends(get_server_context)]
VendorInfoDep = Annotated[VendorInfo, Depends(get_vendor_info)]
FraudValidatorDep = Annotated[FraudHeaderValidator, Depends(get_fraud_validator)]



def get_fraud_headers(
    landlord_id: CurrentLandlordId,
    device: ClientDeviceDep,
    server: ServerContextDep,
    vendor: VendorInfoDep,
) -> dict[str, str]:
    return build_fraud_headers(device, server, vendor, landlord_id)


FraudHeadersDep = Annotated[dict[str, str], Depends(get_fraud_headers)]


@lru_cache
def get_hmrc_api() -> HmrcApi:
    return HttpxHmrcApi(get_settings().hmrc_base_url)


def get_taxpayer_service(
    db: Annotated[Session, Depends(get_db)],
    connections: HmrcServiceDep,
    cipher: Annotated[TokenCipher, Depends(get_token_cipher)],
    hmrc: Annotated[HmrcApi, Depends(get_hmrc_api)],
) -> HmrcTaxpayerService:
    settings = get_settings()
    return HmrcTaxpayerService(
        HmrcTaxpayerRepository(db),
        connections,
        hmrc,
        cipher,
        sandbox="test-api." in settings.hmrc_base_url,
        obligations_test_scenario=settings.hmrc_obligations_test_scenario,
    )


TaxpayerServiceDep = Annotated[HmrcTaxpayerService, Depends(get_taxpayer_service)]
