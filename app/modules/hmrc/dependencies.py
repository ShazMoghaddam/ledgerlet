"""Wiring for the HMRC module. Tests override the cipher and the OAuth client."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.modules.hmrc.crypto import TokenCipher
from app.modules.hmrc.oauth import HttpxOAuthClient, OAuthClient
from app.modules.hmrc.repository import HmrcConnectionRepository
from app.modules.hmrc.service import HmrcConnectionService, OAuthSettings

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
