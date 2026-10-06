"""NINO storage, business discovery and obligations, with HMRC faked."""

from datetime import date

import pytest

from app.core.exceptions import UpstreamError
from app.modules.hmrc.crypto import TokenCipher
from app.modules.hmrc.service import HmrcNotConnectedError
from app.modules.hmrc.taxpayer import HmrcProfileMissingError, HmrcTaxpayerService
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
