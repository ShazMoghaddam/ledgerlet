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
        sandbox: bool = False,
        obligations_test_scenario: str | None = None,
    ) -> None:
        self._repo = repository
        self._tokens = tokens
        self._hmrc = hmrc
        self._cipher = cipher
        self._sandbox = sandbox
        self._obligations_scenario = obligations_test_scenario

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
            test_scenario=api.STATEFUL if self._sandbox else None,
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
        """HMRC's quarterly obligations for this landlord's UK property business.

        Production: filtered by business id and dates at HMRC, and checked again here.
        Sandbox in DYNAMIC mode: HMRC only generates obligations for its own example
        businesses and rejects any filter, so we ask unfiltered and pick the UK
        property group and the requested dates ourselves.
        """
        taxpayer = self._require(landlord_id)
        business_id = taxpayer.uk_property_business_id
        if not business_id:
            raise HmrcProfileMissingError(
                "Choose your UK property business first (discover businesses)"
            )
        scenario = self._obligations_scenario if self._sandbox else None
        sandbox_dynamic = scenario == "DYNAMIC"
        params = (
            {}
            if sandbox_dynamic
            else {
                "typeOfBusiness": UK_PROPERTY,
                "businessId": business_id,
                "fromDate": date_from.isoformat(),
                "toDate": date_to.isoformat(),
            }
        )
        response = self._call(
            landlord_id,
            api.OBLIGATIONS.format(nino=self._nino(taxpayer)),
            api.OBLIGATIONS_VERSION,
            fraud_headers,
            params,
            scenario,
        )
        if response.status_code == 404 and response.body.get("code") == "NO_OBLIGATIONS_FOUND":
            return [], response.body  # nothing due is an answer, not an error
        if not response.ok:
            raise HmrcApiError("show your obligations", response)

        found: dict[tuple[date, date], Obligation] = {}
        for group in response.body.get("obligations", []):
            if not isinstance(group, dict) or group.get("typeOfBusiness") != UK_PROPERTY:
                continue
            if not sandbox_dynamic and group.get("businessId") not in (None, business_id):
                continue
            for d in group.get("obligationDetails", []):
                obligation = _parse_obligation(d)
                if obligation is None:
                    continue  # the raw body below still holds it
                if obligation.period_start < date_from or obligation.period_end > date_to:
                    continue
                found.setdefault((obligation.period_start, obligation.period_end), obligation)
        return sorted(found.values(), key=lambda o: o.period_end), response.body

    def filing_identity(self, landlord_id: UUID) -> tuple[str, str]:
        """(NINO, UK property business id), or 409 saying which is missing."""
        taxpayer = self._require(landlord_id)
        if not taxpayer.uk_property_business_id:
            raise HmrcProfileMissingError(
                "Choose your UK property business first (discover businesses)"
            )
        return self._nino(taxpayer), taxpayer.uk_property_business_id

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
        test_scenario: str | None = None,
    ) -> HmrcResponse:
        response = self._call(landlord_id, path, version, fraud_headers, params, test_scenario)
        if not response.ok:
            raise HmrcApiError(action, response)
        return response

    def _call(
        self,
        landlord_id: UUID,
        path: str,
        version: str,
        fraud_headers: dict[str, str],
        params: dict[str, str] | None = None,
        test_scenario: str | None = None,
    ) -> HmrcResponse:
        token = self._tokens.access_token(landlord_id)  # 409 if not connected
        return self._hmrc.get(path, version, token, fraud_headers, params, test_scenario)


def _parse_obligation(raw: object) -> Obligation | None:
    if not isinstance(raw, dict):
        return None
    try:
        return Obligation(
            period_start=date.fromisoformat(raw["periodStartDate"]),
            period_end=date.fromisoformat(raw["periodEndDate"]),
            due=date.fromisoformat(raw["dueDate"]),
            status=str(raw.get("status", "")),
            received=date.fromisoformat(raw["receivedDate"]) if raw.get("receivedDate") else None,
        )
    except (KeyError, TypeError, ValueError):
        return None
