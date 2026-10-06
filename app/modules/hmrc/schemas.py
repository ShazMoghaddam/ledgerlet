"""The HMRC connection contract. Tokens never appear in any response."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.hmrc.nino import normalise_nino


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


class NinoIn(BaseModel):
    nino: str = Field(examples=["QQ123456C"])

    @field_validator("nino")
    @classmethod
    def _valid(cls, value: str) -> str:
        return normalise_nino(value)


class BusinessIdIn(BaseModel):
    business_id: str = Field(pattern=r"^[A-Z0-9]{6,32}$", examples=["XPIS12345678901"])


class TaxpayerRead(BaseModel):
    nino: str | None  # always masked
    uk_property_business_id: str | None


class BusinessRead(BaseModel):
    business_id: str
    type_of_business: str
    trading_name: str | None


class DiscoveryRead(BaseModel):
    businesses: list[BusinessRead]
    selected_business_id: str | None


class HmrcObligationRead(BaseModel):
    period_start: date
    period_end: date
    due: date
    status: str
    received: date | None


class HmrcObligationsRead(BaseModel):
    obligations: list[HmrcObligationRead]
    hmrc_response: dict[str, Any]  # HMRC's own words, for checking against ours
