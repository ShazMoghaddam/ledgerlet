"""Layer 2: connecting a landlord to HMRC, keeping the tokens fresh, disconnecting.

The OAuth dance, and how it's protected:
1. start():    the landlord asks to connect. We return HMRC's approval URL with a
               sealed `state` (who started it, plus a random nonce, valid 10 minutes).
               The router also puts the nonce in an HttpOnly cookie in that browser.
2. HMRC:       the landlord signs in at HMRC and approves LedgerLet.
3. complete(): HMRC redirects the browser back with a one-time code. We open the
               state (proves it's ours, untampered, recent) and require the cookie
               nonce to match (proves the same browser started it). Only then do we
               swap the code for tokens.
"""

import hmac
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from urllib.parse import urlencode
from uuid import UUID

from app.core.exceptions import ConflictError, DomainError
from app.core.time import as_utc, utc_now
from app.modules.hmrc.crypto import DecryptionError, TokenCipher
from app.modules.hmrc.models import HmrcConnection
from app.modules.hmrc.oauth import HmrcAuthError, OAuthClient, TokenGrant

STATE_PURPOSE = "hmrc-connect"
STATE_MAX_AGE_SECONDS = 600
REFRESH_MARGIN = timedelta(seconds=60)


class HmrcConnectError(DomainError):
    """The approval round-trip failed or couldn't be trusted (400)."""


class HmrcNotConnectedError(ConflictError):
    """No usable HMRC authorisation; the landlord must (re)connect (409)."""


@dataclass(frozen=True)
class OAuthSettings:
    authorize_url: str
    client_id: str
    redirect_uri: str
    scopes: str


@dataclass(frozen=True)
class ConnectStart:
    authorize_url: str
    nonce: str  # goes in the browser cookie


class HmrcConnectionRepositoryProtocol(Protocol):
    def get_for_landlord(self, landlord_id: UUID) -> HmrcConnection | None: ...
    def add(self, connection: HmrcConnection) -> HmrcConnection: ...
    def delete(self, connection: HmrcConnection) -> None: ...
    def commit(self) -> None: ...


class HmrcConnectionService:
    def __init__(
        self,
        repository: HmrcConnectionRepositoryProtocol,
        oauth: OAuthClient,
        cipher: TokenCipher,
        settings: OAuthSettings,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._repo = repository
        self._oauth = oauth
        self._cipher = cipher
        self._settings = settings
        self._clock = clock

    # The round trip

    def start(self, landlord_id: UUID) -> ConnectStart:
        nonce = secrets.token_urlsafe(24)
        state = self._cipher.seal(
            {"purpose": STATE_PURPOSE, "landlord_id": str(landlord_id), "nonce": nonce}
        )
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self._settings.client_id,
                "scope": self._settings.scopes,
                "state": state,
                "redirect_uri": self._settings.redirect_uri,
            }
        )
        return ConnectStart(authorize_url=f"{self._settings.authorize_url}?{query}", nonce=nonce)

    def complete(self, code: str, state: str, cookie_nonce: str | None) -> HmrcConnection:
        try:
            payload = self._cipher.open(state, STATE_MAX_AGE_SECONDS)
        except DecryptionError:
            raise HmrcConnectError("This HMRC approval link is invalid or has expired") from None
        if payload.get("purpose") != STATE_PURPOSE:
            raise HmrcConnectError("This HMRC approval link is invalid")
        if not cookie_nonce or not hmac.compare_digest(cookie_nonce, str(payload.get("nonce"))):
            raise HmrcConnectError("Please start connecting to HMRC again from LedgerLet")

        try:
            grant = self._oauth.exchange_code(code)
        except HmrcAuthError:
            raise HmrcConnectError("HMRC did not accept the approval. Please try again") from None

        landlord_id = UUID(str(payload["landlord_id"]))
        connection = self._repo.get_for_landlord(landlord_id)
        if connection is None:
            connection = HmrcConnection(landlord_id=landlord_id)
            self._store(connection, grant)
            connection.connected_at = self._clock()
            self._repo.add(connection)
        else:
            self._store(connection, grant)
            connection.connected_at = self._clock()
        self._repo.commit()
        return connection

    # Using the connection

    def status(self, landlord_id: UUID) -> HmrcConnection | None:
        return self._repo.get_for_landlord(landlord_id)

    def access_token(self, landlord_id: UUID) -> str:
        """A currently valid HMRC access token, refreshing first if it's about to expire."""
        connection = self._repo.get_for_landlord(landlord_id)
        if connection is None:
            raise HmrcNotConnectedError("Connect LedgerLet to HMRC first")

        if as_utc(connection.access_token_expires_at) - self._clock() > REFRESH_MARGIN:
            return self._cipher.decrypt(connection.access_token_encrypted)

        try:
            grant = self._oauth.refresh(self._cipher.decrypt(connection.refresh_token_encrypted))
        except HmrcAuthError:
            # Refresh tokens are single-use and expire after the 18-month grant.
            # Once refused, the stored pair is useless: remove it and ask to reconnect.
            self._repo.delete(connection)
            self._repo.commit()
            raise HmrcNotConnectedError(
                "LedgerLet's access to HMRC has expired. Please connect again"
            ) from None
        self._store(connection, grant)  # HMRC issues a new refresh token every time
        self._repo.commit()
        return grant.access_token

    def disconnect(self, landlord_id: UUID) -> None:
        connection = self._repo.get_for_landlord(landlord_id)
        if connection is not None:
            self._repo.delete(connection)
            self._repo.commit()

    def _store(self, connection: HmrcConnection, grant: TokenGrant) -> None:
        connection.access_token_encrypted = self._cipher.encrypt(grant.access_token)
        connection.refresh_token_encrypted = self._cipher.encrypt(grant.refresh_token)
        connection.access_token_expires_at = self._clock() + timedelta(seconds=grant.expires_in)
        connection.scope = grant.scope or self._settings.scopes
