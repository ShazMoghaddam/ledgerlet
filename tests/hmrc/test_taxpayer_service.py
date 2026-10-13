"""NINO storage, business discovery and obligations, with HMRC faked."""

from datetime import date

import pytest

from app.core.exceptions import UpstreamError
from app.modules.hmrc.crypto import TokenCipher
from app.modules.hmrc.service import HmrcNotConnectedError
from app.modules.hmrc.taxpayer import (
    HmrcApiError,
    HmrcProfileMissingError,
    HmrcTaxpayerService,
    SandboxOnlyError,
)
from tests.hmrc.fakes import TEST_TOKEN_KEY, FakeHmrcApi, FakeTaxpayerRepository, FakeTokens

FRAUD = {"Gov-Client-Connection-Method": "WEB_APP_VIA_SERVER"}
YEAR = (date(2026, 4, 6), date(2027, 4, 5))


@pytest.fixture
def api() -> FakeHmrcApi:
    return FakeHmrcApi()


@pytest.fixture
def tokens() -> FakeTokens:
    return FakeTokens()


@pytest.fixture
def repo() -> FakeTaxpayerRepository:
    return FakeTaxpayerRepository()


@pytest.fixture
def cipher() -> TokenCipher:
    return TokenCipher(TEST_TOKEN_KEY)


@pytest.fixture
def service(repo, tokens, api, cipher) -> HmrcTaxpayerService:
    return HmrcTaxpayerService(repo, tokens, api, cipher)


def test_nino_is_stored_encrypted_and_shown_masked(service, repo, cipher, landlord_id) -> None:
    taxpayer = service.set_nino(landlord_id, "oe 18 06 77 a")
    assert "OE180677A" not in taxpayer.nino_encrypted
    assert cipher.decrypt(taxpayer.nino_encrypted) == "OE180677A"
    assert service.masked_nino(taxpayer) == "OE****77A"


def test_changing_nino_clears_the_business(service, landlord_id) -> None:
    service.set_nino(landlord_id, "OE180677A")
    service.set_business(landlord_id, "XPIS12345678901")
    assert service.set_nino(landlord_id, "AB123456C").uk_property_business_id is None


def test_discovery_selects_the_single_uk_property_business(service, api, landlord_id) -> None:
    service.set_nino(landlord_id, "OE180677A")
    businesses, taxpayer = service.discover_businesses(landlord_id, FRAUD)
    assert {b.type_of_business for b in businesses} == {"uk-property", "self-employment"}
    assert taxpayer.uk_property_business_id == "XPIS12345678901"

    call = api.calls[0]
    assert call["path"] == "/individuals/business/details/OE180677A/list"
    assert call["version"] == "2.0"
    assert call["token"] == "live-access-token"
    assert call["fraud_headers"] == FRAUD  # every HMRC call carries them


def test_discovery_leaves_choice_open_when_ambiguous(service, api, landlord_id) -> None:
    api.businesses.append({"typeOfBusiness": "uk-property", "businessId": "XPIS99999999999"})
    service.set_nino(landlord_id, "OE180677A")
    _, taxpayer = service.discover_businesses(landlord_id, FRAUD)
    assert taxpayer.uk_property_business_id is None


def test_discovery_with_no_businesses(service, api, landlord_id) -> None:
    api.businesses = []
    service.set_nino(landlord_id, "OE180677A")
    businesses, taxpayer = service.discover_businesses(landlord_id, FRAUD)
    assert businesses == [] and taxpayer.uk_property_business_id is None


def test_obligations_are_parsed_and_sorted(service, api, landlord_id) -> None:
    service.set_nino(landlord_id, "OE180677A")
    service.discover_businesses(landlord_id, FRAUD)
    found, raw = service.obligations(landlord_id, FRAUD, *YEAR)
    assert [(o.period_end, o.status) for o in found] == [
        (date(2026, 7, 5), "fulfilled"),
        (date(2026, 10, 5), "open"),
    ]
    assert found[0].received == date(2026, 8, 1) and found[1].received is None
    assert "obligations" in raw
    params = api.calls[-1]["params"]
    assert params == {
        "typeOfBusiness": "uk-property",
        "businessId": "XPIS12345678901",
        "fromDate": "2026-04-06",
        "toDate": "2027-04-05",
    }
    assert api.calls[-1]["version"] == "3.0"


def test_hmrc_refusal_is_reported_with_its_reference(service, api, landlord_id) -> None:
    service.set_nino(landlord_id, "OE180677A")
    api.fail_with = (404, {"code": "MATCHING_RESOURCE_NOT_FOUND", "message": "Not found"})
    with pytest.raises(UpstreamError, match="MATCHING_RESOURCE_NOT_FOUND.*corr-123"):
        service.discover_businesses(landlord_id, FRAUD)


def test_needs_a_nino_first(service, landlord_id) -> None:
    with pytest.raises(HmrcProfileMissingError):
        service.discover_businesses(landlord_id, FRAUD)


def test_obligations_need_a_business_first(service, api, landlord_id) -> None:
    api.businesses = []
    service.set_nino(landlord_id, "OE180677A")
    with pytest.raises(HmrcProfileMissingError):
        service.obligations(landlord_id, FRAUD, *YEAR)


def test_needs_an_hmrc_connection(repo, api, cipher, landlord_id) -> None:
    service = HmrcTaxpayerService(repo, FakeTokens(connected=False), api, cipher)
    service.set_nino(landlord_id, "OE180677A")
    with pytest.raises(HmrcNotConnectedError):
        service.discover_businesses(landlord_id, FRAUD)
    assert api.calls == []  # never called HMRC without a token


def test_sandbox_discovery_asks_for_stateful_data(repo, tokens, api, cipher, landlord_id) -> None:
    service = HmrcTaxpayerService(repo, tokens, api, cipher, sandbox=True)
    service.set_nino(landlord_id, "OE180677A")
    service.discover_businesses(landlord_id, FRAUD)
    assert api.calls[-1]["test_scenario"] == "STATEFUL"


def test_production_never_sends_test_scenarios(repo, tokens, api, cipher, landlord_id) -> None:
    service = HmrcTaxpayerService(
        repo, tokens, api, cipher, sandbox=False, obligations_test_scenario="STATEFUL"
    )
    service.set_nino(landlord_id, "OE180677A")
    service.discover_businesses(landlord_id, FRAUD)
    service.obligations(landlord_id, FRAUD, *YEAR)
    assert {c["test_scenario"] for c in api.calls} == {None}


def test_obligations_scenario_is_configurable_in_sandbox(
    repo, tokens, api, cipher, landlord_id
) -> None:
    service = HmrcTaxpayerService(
        repo, tokens, api, cipher, sandbox=True, obligations_test_scenario="STATEFUL"
    )
    service.set_nino(landlord_id, "OE180677A")
    service.discover_businesses(landlord_id, FRAUD)
    service.obligations(landlord_id, FRAUD, *YEAR)
    assert api.calls[-1]["test_scenario"] == "STATEFUL"


def _period(start: str, end: str, due: str, status: str = "open") -> dict:
    return {"periodStartDate": start, "periodEndDate": end, "dueDate": due, "status": status}


def test_nothing_due_is_an_empty_list_not_an_error(service, api, landlord_id) -> None:
    service.set_nino(landlord_id, "OE180677A")
    service.discover_businesses(landlord_id, FRAUD)
    api.fail_with = (404, {"code": "NO_OBLIGATIONS_FOUND", "message": "none"})
    found, raw = service.obligations(landlord_id, FRAUD, *YEAR)
    assert found == [] and raw["code"] == "NO_OBLIGATIONS_FOUND"


def test_other_hmrc_errors_still_raise(service, api, landlord_id) -> None:
    service.set_nino(landlord_id, "OE180677A")
    service.discover_businesses(landlord_id, FRAUD)
    api.fail_with = (403, {"code": "CLIENT_OR_AGENT_NOT_AUTHORISED", "message": "no"})
    with pytest.raises(UpstreamError):
        service.obligations(landlord_id, FRAUD, *YEAR)


def test_production_ignores_other_businesses(service, api, landlord_id) -> None:
    api.extra_groups = [
        {
            "typeOfBusiness": "self-employment",
            "businessId": "XBIS12345678901",
            "obligationDetails": [_period("2026-04-06", "2026-07-05", "2026-08-07")],
        },
        {
            "typeOfBusiness": "uk-property",
            "businessId": "XPIS00000000000",  # someone else's property business
            "obligationDetails": [_period("2026-04-06", "2027-01-05", "2027-02-07")],
        },
    ]
    service.set_nino(landlord_id, "OE180677A")
    service.discover_businesses(landlord_id, FRAUD)
    found, _ = service.obligations(landlord_id, FRAUD, *YEAR)
    assert [o.period_end for o in found] == [date(2026, 7, 5), date(2026, 10, 5)]


def test_sandbox_dynamic_mode_matches_what_hmrc_actually_returns(
    repo, tokens, api, cipher, landlord_id
) -> None:
    """Shaped like the real sandbox reply: example businesses only, two tax years, repeats."""
    api.obligation_details = []
    api.extra_groups = [
        {
            "typeOfBusiness": "self-employment",
            "businessId": "XBIS12345678901",
            "obligationDetails": [_period("2026-04-06", "2027-01-05", "2027-02-07")],
        },
        {
            "typeOfBusiness": "uk-property",
            "businessId": "XPIS12345678901",  # not ours: the sandbox's example business
            "obligationDetails": [
                _period("2026-04-06", "2026-10-05", "2026-11-07"),
                _period("2026-04-06", "2027-01-05", "2027-02-07"),
                _period("2026-04-06", "2027-04-05", "2027-05-07"),
                _period("2026-04-06", "2027-01-05", "2027-02-07"),  # repeated
                _period("2027-04-06", "2027-07-05", "2027-08-07"),  # next tax year
            ],
        },
    ]
    service = HmrcTaxpayerService(
        repo, tokens, api, cipher, sandbox=True, obligations_test_scenario="DYNAMIC"
    )
    service.set_nino(landlord_id, "OE180677A")
    service.set_business(landlord_id, "XDIS36257256364")  # the business we created
    found, _ = service.obligations(landlord_id, FRAUD, *YEAR)

    assert [(o.period_end, o.due) for o in found] == [
        (date(2026, 10, 5), date(2026, 11, 7)),
        (date(2027, 1, 5), date(2027, 2, 7)),
        (date(2027, 4, 5), date(2027, 5, 7)),
    ]
    call = api.calls[-1]
    assert call["params"] == {}  # the sandbox rejects every filter in DYNAMIC mode
    assert call["test_scenario"] == "DYNAMIC"


def test_sandbox_can_create_a_test_property_business(
    repo, tokens, api, cipher, landlord_id
) -> None:
    service = HmrcTaxpayerService(repo, tokens, api, cipher, sandbox=True)
    service.set_nino(landlord_id, "OE180677A")
    api.businesses = []  # HMRC deleted the old one after 7 days
    _, taxpayer = service.create_test_property_business(landlord_id, FRAUD, 2026)
    post = next(c for c in api.calls if c.get("method") == "POST")
    assert post["path"] == "/individuals/self-assessment-test-support/business/OE180677A"
    assert post["body"]["quarterlyTypeChoice"]["taxYearOfChoice"] == "2026-27"
    assert post["body"]["firstAccountingPeriodStartDate"] == "2026-04-06"
    assert taxpayer.uk_property_business_id == "XPIS99999999999"  # found and selected


def test_test_businesses_are_never_made_outside_the_sandbox(service, api, landlord_id) -> None:
    service.set_nino(landlord_id, "OE180677A")
    with pytest.raises(SandboxOnlyError):
        service.create_test_property_business(landlord_id, FRAUD, 2026)
    assert api.calls == []


def test_a_refused_test_business_names_hmrcs_reason(repo, tokens, api, cipher, landlord_id) -> None:
    service = HmrcTaxpayerService(repo, tokens, api, cipher, sandbox=True)
    service.set_nino(landlord_id, "OE180677A")
    api.post_response = (400, {"code": "RULE_TYPE_OF_BUSINESS_INCORRECT", "message": "No"})
    with pytest.raises(HmrcApiError, match="RULE_TYPE_OF_BUSINESS_INCORRECT"):
        service.create_test_property_business(landlord_id, FRAUD, 2026)
