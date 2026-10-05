"""The HMRC connection contract. Tokens never appear in any response."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConnectStartRead(BaseModel):
    authorize_url: str


class ConnectionStatus(BaseModel):
    connected: bool
    connected_at: datetime | None = None
    access_token_expires_at: datetime | None = None
    scope: str | None = None


class ScreenIn(BaseModel):
    width: int = Field(gt=0, le=100_000)
    height: int = Field(gt=0, le=100_000)
    scaling_factor: float = Field(gt=0, le=20)
    colour_depth: int = Field(gt=0, le=128)


class ClientDevice(BaseModel):
    """Sent by the browser in the X-LedgerLet-Device header, as JSON."""

    model_config = ConfigDict(extra="forbid")

    device_id: UUID
    js_user_agent: str = Field(min_length=1, max_length=1024)
    screens: list[ScreenIn] = Field(min_length=1, max_length=16)
    window_width: int = Field(gt=0, le=100_000)
    window_height: int = Field(gt=0, le=100_000)
    utc_offset_minutes: int = Field(ge=-14 * 60, le=14 * 60)


class FraudHeaderCheck(BaseModel):
    headers_sent: dict[str, str]
    hmrc_response: dict[str, Any]
