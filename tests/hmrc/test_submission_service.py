"""Submitting cumulative updates: rules, what's sent, and the audit trail. HMRC faked."""

from datetime import UTC, date, datetime

import pytest

from app.core.exceptions import BusinessRuleError, UpstreamError
from app.modules.hmrc.service import HmrcNotConnectedError
from app.modules.hmrc.submission import HmrcSubmissionService
from app.modules.hmrc.taxpayer import HmrcProfileMissingError
from app.modules.tax.periods import PeriodBasis
from app.modules.transactions.categories import TransactionCategory as C
from tests.hmrc.fakes import FakeHmrcApi, FakeSubmissionRepository, FakeTokens

FRAUD = {"Gov-Client-Connection-Method": "WEB_APP_VIA_SERVER"}
STANDARD = PeriodBasis.STANDARD
TODAY = date(2026, 10, 8)  # Q2 (to 5 Oct) has ended; Q3 hasn't


class FakeTotals:
    def __init__(self) -> None:
        self.asked: list[tuple[date, date]] = []

    def period_totals(self, landlord_id, date_from, date_to):
        self.asked.append((date_from, date_to))
        totals = dict.fromkeys(C, 0)
        totals[C.RENTAL_INCOME] = 240051
        totals[C.RESIDENTIAL_FINANCE_COSTS] = 30000
        return totals


class FakeIdentity:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready

    def filing_identity(self, landlord_id):
        if not self.ready:
            raise HmrcProfileMissingError("Add your National Insurance number first")
        return "OE180677A", "XDIS36257256364"


@pytest.fixture
def api() -> FakeHmrcApi:
    return FakeHmrcApi()


@pytest.fixture
def repo() -> FakeSubmissionRepository:
    return FakeSubmissionRepository()


def make(repo, api, *, identity=None, tokens=None, today=TODAY) -> HmrcSubmissionService:
    return HmrcSubmissionService(
        repo,
        FakeTotals(),
        identity or FakeIdentity(),
        tokens or FakeTokens(),
        api,
        today=lambda: today,
        clock=lambda: datetime(2026, 10, 8, 12, 0, tzinfo=UTC),
    )


def submit(service, landlord_id, quarter=2, consolidated=False):
    return service.submit(landlord_id, 2026, quarter, STANDARD, consolidated, FRAUD)


def test_preview_sends_and_records_nothing(repo, api, landlord_id) -> None:
    preview = make(repo, api).preview(landlord_id, 2026, 2, STANDARD, False)
    assert preview.body["toDate"] == "2026-10-05"
    assert preview.body["ukProperty"]["income"]["periodAmount"] == 2400.51
    assert api.calls == [] and repo.items == []


def test_successful_submission_is_sent_correctly_and_recorded(repo, api, landlord_id) -> None:
    record = submit(make(repo, api), landlord_id)

    call = api.calls[-1]
    assert call["method"] == "PUT"
    assert call["path"] == (
        "/individuals/business/property/uk/OE180677A/XDIS36257256364/cumulative/2026-27"
    )
    assert call["version"] == "6.0"
    assert call["token"] == "live-access-token"
    assert call["fraud_headers"] == FRAUD
    assert call["body"]["fromDate"] == "2026-04-06"  # cumulative from the year start

    assert record.succeeded and record.status_code == 204
    assert record.hmrc_correlation_id == "corr-put"
    assert record.request_body == call["body"]  # the record is exactly what was sent
    assert "OE180677A" not in str(record.request_body)  # no NINO in the audit row
    assert repo.commit_count == 1


def test_hmrc_refusal_is_recorded_then_raised(repo, api, landlord_id) -> None:
    api.put_response = (400, {"code": "RULE_INCORRECT_OR_EMPTY_BODY_SUBMITTED", "message": "x"})
    with pytest.raises(UpstreamError, match="RULE_INCORRECT_OR_EMPTY_BODY_SUBMITTED"):
        submit(make(repo, api), landlord_id)
    assert len(repo.items) == 1 and repo.items[0].succeeded is False
    assert repo.items[0].response_body["code"] == "RULE_INCORRECT_OR_EMPTY_BODY_SUBMITTED"


def test_quarter_still_running_is_refused_without_calling_hmrc(repo, api, landlord_id) -> None:
    with pytest.raises(BusinessRuleError, match="5 January 2027"):
        submit(make(repo, api), landlord_id, quarter=3)
    assert api.calls == [] and repo.items == []


def test_last_day_of_quarter_is_still_too_early(repo, api, landlord_id) -> None:
    with pytest.raises(BusinessRuleError):
        submit(make(repo, api, today=date(2026, 10, 5)), landlord_id, quarter=2)


def test_cannot_go_back_to_an_earlier_end_date(repo, api, landlord_id) -> None:
    service = make(repo, api)
    submit(service, landlord_id, quarter=2)
    with pytest.raises(BusinessRuleError, match="5 October 2026"):
        submit(service, landlord_id, quarter=1)
    submit(service, landlord_id, quarter=2)  # resubmitting the same quarter is fine
    assert [r.quarter for r in repo.items] == [2, 2]


def test_failed_attempt_does_not_block_earlier_quarters(repo, api, landlord_id) -> None:
    service = make(repo, api)
    api.put_response = (400, {"code": "X", "message": "x"})
    with pytest.raises(UpstreamError):
        submit(service, landlord_id, quarter=2)
    api.put_response = (204, {})
    submit(service, landlord_id, quarter=1)


def test_needs_nino_and_business(repo, api, landlord_id) -> None:
    with pytest.raises(HmrcProfileMissingError):
        submit(make(repo, api, identity=FakeIdentity(ready=False)), landlord_id)
    assert api.calls == [] and repo.items == []


def test_needs_hmrc_connection(repo, api, landlord_id) -> None:
    with pytest.raises(HmrcNotConnectedError):
        submit(make(repo, api, tokens=FakeTokens(connected=False)), landlord_id)
    assert api.calls == [] and repo.items == []


def test_consolidated_submission(repo, api, landlord_id) -> None:
    record = submit(make(repo, api), landlord_id, consolidated=True)
    assert set(record.request_body["ukProperty"]["expenses"]) == {
        "consolidatedExpenses",
        "residentialFinancialCost",
    }
