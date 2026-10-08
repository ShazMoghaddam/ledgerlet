"""Layer 2: sending a cumulative quarterly update to HMRC, and keeping the audit trail.

Rules, in the order they're checked:
1. The quarter must have ended. (Updates are cumulative to the end of a quarter.)
2. Within a tax year, a new update may not stop earlier than one HMRC already
   accepted. HMRC requires each submission to reach the same end date or later.
3. Every attempt that reaches HMRC is recorded, success or failure, before the
   result is returned or raised. Nothing is recorded if we never called HMRC.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID

from app.core.exceptions import BusinessRuleError
from app.core.time import uk_today, utc_now
from app.modules.hmrc import api
from app.modules.hmrc.api import HmrcApi
from app.modules.hmrc.mapping import build_uk_property_body, to_json
from app.modules.hmrc.models import HmrcSubmission
from app.modules.hmrc.taxpayer import HmrcApiError
from app.modules.tax.periods import PeriodBasis, UpdatePeriod, tax_year_label, update_period
from app.modules.transactions.categories import TransactionCategory


class PeriodTotals(Protocol):
    def period_totals(
        self, landlord_id: UUID, date_from: date, date_to: date
    ) -> dict[TransactionCategory, int]: ...


class FilingIdentity(Protocol):
    def filing_identity(self, landlord_id: UUID) -> tuple[str, str]: ...


class AccessTokens(Protocol):
    def access_token(self, landlord_id: UUID) -> str: ...


class SubmissionRepositoryProtocol(Protocol):
    def add(self, submission: HmrcSubmission) -> HmrcSubmission: ...
    def list_for_landlord(
        self, landlord_id: UUID, tax_year: int | None = None
    ) -> list[HmrcSubmission]: ...
    def commit(self) -> None: ...


@dataclass(frozen=True)
class Preview:
    period: UpdatePeriod
    body: dict[str, Any]


class HmrcSubmissionService:
    def __init__(
        self,
        repository: SubmissionRepositoryProtocol,
        totals: PeriodTotals,
        identity: FilingIdentity,
        tokens: AccessTokens,
        hmrc: HmrcApi,
        today: Callable[[], date] = uk_today,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._repo = repository
        self._totals = totals
        self._identity = identity
        self._tokens = tokens
        self._hmrc = hmrc
        self._today = today
        self._clock = clock

    def preview(
        self,
        landlord_id: UUID,
        tax_year: int,
        quarter: int,
        basis: PeriodBasis,
        consolidated_expenses: bool,
    ) -> Preview:
        """Exactly what would be sent. Calls nothing, records nothing."""
        period = update_period(tax_year, quarter, basis)
        totals = self._totals.period_totals(landlord_id, period.start, period.end)
        body = build_uk_property_body(
            totals, period.start, period.end, consolidated_expenses=consolidated_expenses
        )
        return Preview(period=period, body=to_json(body))

    def submit(
        self,
        landlord_id: UUID,
        tax_year: int,
        quarter: int,
        basis: PeriodBasis,
        consolidated_expenses: bool,
        fraud_headers: dict[str, str],
    ) -> HmrcSubmission:
        preview = self.preview(landlord_id, tax_year, quarter, basis, consolidated_expenses)
        period = preview.period

        if self._today() <= period.end:
            raise BusinessRuleError(
                f"Quarter {quarter} runs until {period.end:%-d %B %Y}. "
                "It can be submitted once it has ended."
            )
        latest_accepted = max(
            (
                s.period_end
                for s in self._repo.list_for_landlord(landlord_id, tax_year)
                if s.succeeded
            ),
            default=None,
        )
        if latest_accepted and period.end < latest_accepted:
            raise BusinessRuleError(
                f"HMRC already has figures up to {latest_accepted:%-d %B %Y}. A new update "
                "must reach that date or later; resubmit that quarter to make corrections."
            )

        nino, business_id = self._identity.filing_identity(landlord_id)
        token = self._tokens.access_token(landlord_id)  # 409 if not connected
        response = self._hmrc.put(
            api.UK_PROPERTY_CUMULATIVE.format(
                nino=nino, business_id=business_id, tax_year=tax_year_label(tax_year)
            ),
            api.PROPERTY_BUSINESS_VERSION,
            token,
            fraud_headers,
            preview.body,
        )

        record = self._repo.add(
            HmrcSubmission(
                landlord_id=landlord_id,
                business_id=business_id,
                tax_year=tax_year,
                quarter=quarter,
                period_start=period.start,
                period_end=period.end,
                consolidated_expenses=consolidated_expenses,
                request_body=preview.body,
                status_code=response.status_code,
                succeeded=response.ok,
                hmrc_correlation_id=response.correlation_id,
                response_body=response.body,
                submitted_at=self._clock(),
            )
        )
        self._repo.commit()  # the attempt is on record before anything else happens
        if not response.ok:
            raise HmrcApiError("accept this update", response)
        return record

    def history(self, landlord_id: UUID, tax_year: int | None = None) -> list[HmrcSubmission]:
        return self._repo.list_for_landlord(landlord_id, tax_year)
