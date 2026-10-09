"""The HMRC connection contract. Tokens never appear in any response."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.hmrc.nino import normalise_nino
from app.modules.tax.periods import PeriodBasis

# A path in our app: starts with one "/", never "//" (another site) and never a backslash.
RETURN_TO_PATTERN = r"^/([A-Za-z0-9_.~?=&%-][A-Za-z0-9/_.~?=&%-]*)?$"


class ConnectStartIn(BaseModel):
    """Where to send the landlord back to in the app once HMRC is done.

    Only a path inside our own app is accepted ("/tax/2026/q2", never
    "https://..." or "//evil.example"), so the callback can't be used to
    bounce people to another site.
    """

    model_config = ConfigDict(extra="forbid")

    return_to: str = Field(default="/settings/hmrc", max_length=200, pattern=RETURN_TO_PATTERN)


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


class SubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quarter: int = Field(ge=1, le=4, description="Cumulative from the start of the tax year")
    tax_year: int | None = Field(default=None, ge=2020, le=2100, examples=[2026])
    basis: PeriodBasis | None = None  # defaults to the landlord's saved setting
    consolidated_expenses: bool = False


class SubmissionPreviewRead(BaseModel):
    tax_year_label: str
    quarter: int
    period_start: date
    period_end: date
    body: dict[str, Any]  # exactly what would be sent to HMRC


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: str
    tax_year: int
    quarter: int
    period_start: date
    period_end: date
    consolidated_expenses: bool
    succeeded: bool
    status_code: int
    hmrc_correlation_id: str | None
    submitted_at: datetime
    request_body: dict[str, Any]
    response_body: dict[str, Any]
