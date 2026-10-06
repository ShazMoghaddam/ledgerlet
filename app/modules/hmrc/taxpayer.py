"""Layer 2: the landlord's identity at HMRC, their businesses, and their obligations.

Read-only towards HMRC. Every call carries the landlord's fresh access token
(refreshed automatically) and this request's fraud prevention headers.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol
from uuid import UUID

from app.core.exceptions import ConflictError, UpstreamError
from app.modules.hmrc import api
from app.modules.hmrc.api import HmrcApi, HmrcResponse
from app.modules.hmrc.crypto import TokenCipher
from app.modules.hmrc.models import HmrcTaxpayer
from app.modules.hmrc.nino import mask_nino, normalise_nino

UK_PROPERTY = "uk-property"


class HmrcApiError(UpstreamError):
    def __init__(self, action: str, response: HmrcResponse) -> None:
        code = response.body.get("code", "UNKNOWN")
        message = response.body.get("message", "no message")
        ref = f" (HMRC reference {response.correlation_id})" if response.correlation_id else ""
        super().__init__(f"HMRC refused to {action}: {code}: {message}{ref}")
        self.response = response


class HmrcProfileMissingError(ConflictError):
    """The landlord hasn't told us their NINO, or which business to use (409)."""


class AccessTokens(Protocol):
    def access_token(self, landlord_id: UUID) -> str: ...


class TaxpayerRepositoryProtocol(Protocol):
    def get_for_landlord(self, landlord_id: UUID) -> HmrcTaxpayer | None: ...
    def add(self, taxpayer: HmrcTaxpayer) -> HmrcTaxpayer: ...
    def commit(self) -> None: ...


@dataclass(frozen=True)
class Business:
    business_id: str
    type_of_business: str
    trading_name: str | None


@dataclass(frozen=True)
class Obligation:
    period_start: date
    period_end: date
    due: date
    status: str  # "open" or "fulfilled"
    received: date | None


class HmrcTaxpayerService:
    def __init__(
        self,
        repository: TaxpayerRepositoryProtocol,
        tokens: AccessTokens,
        hmrc: HmrcApi,
        cipher: TokenCipher,
    ) -> None:
        self._repo = repository
        self._tokens = tokens
        self._hmrc = hmrc
        self._cipher = cipher

    # The landlord's details

    def profile(self, landlord_id: UUID) -> HmrcTaxpayer | None:
        return self._repo.get_for_landlord(landlord_id)

    def masked_nino(self, taxpayer: HmrcTaxpayer) -> str:
        return mask_nino(self._cipher.decrypt(taxpayer.nino_encrypted))

    def set_nino(self, landlord_id: UUID, raw_nino: str) -> HmrcTaxpayer:
        nino = normalise_nino(raw_nino)  # ValueError -> 422 at the schema layer first
        taxpayer = self._repo.get_for_landlord(landlord_id)
        if taxpayer is None:
            taxpayer = self._repo.add(
                HmrcTaxpayer(landlord_id=landlord_id, nino_encrypted=self._cipher.encrypt(nino))
            )
        else:
            taxpayer.nino_encrypted = self._cipher.encrypt(nino)
            taxpayer.uk_property_business_id = None  # a different person's businesses differ
        self._repo.commit()
        return taxpayer

    def set_business(self, landlord_id: UUID, business_id: str) -> HmrcTaxpayer:
        taxpayer = self._require(landlord_id)
        taxpayer.uk_property_business_id = business_id
        self._repo.commit()
        return taxpayer

    # Reading from HMRC

    def discover_businesses(
        self, landlord_id: UUID, fraud_headers: dict[str, str]
    ) -> tuple[list[Business], HmrcTaxpayer]:
        """List the landlord's businesses at HMRC; if exactly one is UK property, use it."""
        taxpayer = self._require(landlord_id)
        response = self._get(
            landlord_id,
            "list your businesses",
            api.LIST_BUSINESSES.format(nino=self._nino(taxpayer)),
            api.BUSINESS_DETAILS_VERSION,
            fraud_headers,
        )
        businesses = [
            Business(
                business_id=str(b.get("businessId", "")),
                type_of_business=str(b.get("typeOfBusiness", "")),
                trading_name=b.get("tradingName"),
            )
            for b in response.body.get("listOfBusinesses", [])
            if isinstance(b, dict)
        ]
        uk = [b for b in businesses if b.type_of_business == UK_PROPERTY]
        if len(uk) == 1 and taxpayer.uk_property_business_id != uk[0].business_id:
            taxpayer.uk_property_business_id = uk[0].business_id
            self._repo.commit()
        return businesses, taxpayer

    def obligations(
        self,
        landlord_id: UUID,
        fraud_headers: dict[str, str],
        date_from: date,
        date_to: date,
    ) -> tuple[list[Obligation], dict[str, Any]]:
        taxpayer = self._require(landlord_id)
        if not taxpayer.uk_property_business_id:
            raise HmrcProfileMissingError(
                "Choose your UK property business first (discover businesses)"
            )
        response = self._get(
            landlord_id,
            "show your obligations",
            api.OBLIGATIONS.format(nino=self._nino(taxpayer)),
            api.OBLIGATIONS_VERSION,
            fraud_headers,
            params={
                "typeOfBusiness": UK_PROPERTY,
                "businessId": taxpayer.uk_property_business_id,
                "fromDate": date_from.isoformat(),
                "toDate": date_to.isoformat(),
            },
        )
        found: list[Obligation] = []
        for group in response.body.get("obligations", []):
            for d in group.get("obligationDetails", []) if isinstance(group, dict) else []:
                try:
                    found.append(
                        Obligation(
                            period_start=date.fromisoformat(d["periodStartDate"]),
                            period_end=date.fromisoformat(d["periodEndDate"]),
                            due=date.fromisoformat(d["dueDate"]),
                            status=str(d.get("status", "")),
                            received=date.fromisoformat(d["receivedDate"])
                            if d.get("receivedDate")
                            else None,
                        )
                    )
                except (KeyError, TypeError, ValueError):
                    continue  # keep the raw body below; never drop HMRC's data silently
        found.sort(key=lambda o: o.period_start)
        return found, response.body

    # Helpers

    def _require(self, landlord_id: UUID) -> HmrcTaxpayer:
        taxpayer = self._repo.get_for_landlord(landlord_id)
        if taxpayer is None:
            raise HmrcProfileMissingError("Add your National Insurance number first")
        return taxpayer

    def _nino(self, taxpayer: HmrcTaxpayer) -> str:
        return self._cipher.decrypt(taxpayer.nino_encrypted)

    def _get(
        self,
        landlord_id: UUID,
        action: str,
        path: str,
        version: str,
        fraud_headers: dict[str, str],
        params: dict[str, str] | None = None,
    ) -> HmrcResponse:
        token = self._tokens.access_token(landlord_id)  # 409 if not connected
        response = self._hmrc.get(path, version, token, fraud_headers, params)
        if not response.ok:
            raise HmrcApiError(action, response)
        return response
