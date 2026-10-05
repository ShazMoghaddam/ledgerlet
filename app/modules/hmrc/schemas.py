"""The HMRC connection contract. Tokens never appear in any response."""

from datetime import datetime

from pydantic import BaseModel


class ConnectStartRead(BaseModel):
    authorize_url: str


class ConnectionStatus(BaseModel):
    connected: bool
    connected_at: datetime | None = None
    access_token_expires_at: datetime | None = None
    scope: str | None = None
