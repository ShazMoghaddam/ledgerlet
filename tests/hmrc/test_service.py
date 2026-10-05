"""The HMRC connection round trip and token lifecycle, with HMRC faked."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet

from app.modules.hmrc.crypto import TokenCipher
from app.modules.hmrc.service import (
    HmrcConnectError,
    HmrcConnectionService,
    HmrcNotConnectedError,
)
from tests.hmrc.fakes import (
    TEST_OAUTH_SETTINGS,
    TEST_TOKEN_KEY,
    FakeConnectionRepository,
    FakeOAuthClient,
)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def repo() -> FakeConnectionRepository:
    return FakeConnectionRepository()


@pytest.fixture
def oauth() -> FakeOAuthClient:
    return FakeOAuthClient()


@pytest.fixture
def cipher() -> TokenCipher:
    return TokenCipher(TEST_TOKEN_KEY)


@pytest.fixture
def service(repo, oauth, cipher, clock) -> HmrcConnectionService:
    return HmrcConnectionService(repo, oauth, cipher, TEST_OAUTH_SETTINGS, clock=clock)


def state_from(url: str) -> str:
    return parse_qs(urlparse(url).query)["state"][0]


def connect(service: HmrcConnectionService, landlord_id: UUID):
    start = service.start(landlord_id)
    return service.complete("good-code", state_from(start.authorize_url), start.nonce)


def test_authorize_url_asks_hmrc_for_the_right_things(service, landlord_id) -> None:
    query = parse_qs(urlparse(service.start(landlord_id).authorize_url).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["test-client-id"]
    assert query["scope"] == ["read:self-assessment write:self-assessment"]
    assert query["redirect_uri"] == ["http://localhost:8000/api/v1/hmrc/callback"]
    assert str(landlord_id) not in query["state"][0]  # sealed, not readable


def test_complete_stores_tokens_encrypted(service, repo, cipher, landlord_id) -> None:
    connection = connect(service, landlord_id)
    assert repo.items[landlord_id] is connection
    assert "access-1" not in connection.access_token_encrypted
    assert "refresh-1" not in connection.refresh_token_encrypted
    assert cipher.decrypt(connection.access_token_encrypted) == "access-1"


def test_nonce_from_another_browser_is_rejected(service, landlord_id) -> None:
    start = service.start(landlord_id)
    with pytest.raises(HmrcConnectError):
        service.complete("good-code", state_from(start.authorize_url), "someone-elses-nonce")


def test_missing_cookie_is_rejected(service, landlord_id) -> None:
    start = service.start(landlord_id)
    with pytest.raises(HmrcConnectError):
        service.complete("good-code", state_from(start.authorize_url), None)


def test_forged_state_is_rejected(service, landlord_id) -> None:
    start = service.start(landlord_id)
    with pytest.raises(HmrcConnectError):
        service.complete("good-code", "not-a-sealed-state", start.nonce)


def test_state_sealed_with_another_key_is_rejected(service, oauth, repo, clock) -> None:
    attacker = HmrcConnectionService(
        repo, oauth, TokenCipher(Fernet.generate_key().decode()), TEST_OAUTH_SETTINGS, clock
    )
    start = attacker.start(uuid4())
    with pytest.raises(HmrcConnectError):
        service.complete("good-code", state_from(start.authorize_url), start.nonce)


def test_hmrc_refusing_the_code_is_reported(service, landlord_id) -> None:
    start = service.start(landlord_id)
    with pytest.raises(HmrcConnectError):
        service.complete("bad-code", state_from(start.authorize_url), start.nonce)


def test_fresh_token_is_used_without_refreshing(service, oauth, landlord_id) -> None:
    connect(service, landlord_id)
    assert service.access_token(landlord_id) == "access-1"
    assert ("refresh", "refresh-1") not in oauth.calls


def test_token_near_expiry_is_refreshed_and_rotated(
    service, oauth, repo, cipher, clock, landlord_id
) -> None:
    connect(service, landlord_id)
    clock.now += timedelta(hours=4) - timedelta(seconds=30)  # inside the 60s margin
    assert service.access_token(landlord_id) == "access-2"
    stored = repo.items[landlord_id]
    assert cipher.decrypt(stored.refresh_token_encrypted) == "refresh-2"
    assert stored.access_token_expires_at == clock.now + timedelta(hours=4)


def test_refused_refresh_disconnects_and_asks_to_reconnect(
    service, oauth, repo, clock, landlord_id
) -> None:
    connect(service, landlord_id)
    oauth.live_refresh_tokens.clear()  # e.g. the 18-month grant ended
    clock.now += timedelta(hours=5)
    with pytest.raises(HmrcNotConnectedError):
        service.access_token(landlord_id)
    assert landlord_id not in repo.items


def test_not_connected(service, landlord_id) -> None:
    with pytest.raises(HmrcNotConnectedError):
        service.access_token(landlord_id)


def test_reconnecting_replaces_the_tokens(service, oauth, cipher, landlord_id) -> None:
    connect(service, landlord_id)
    oauth.valid_codes.add("good-code")
    second = connect(service, landlord_id)
    assert cipher.decrypt(second.access_token_encrypted) == "access-2"


def test_disconnect(service, repo, landlord_id) -> None:
    connect(service, landlord_id)
    service.disconnect(landlord_id)
    assert service.status(landlord_id) is None
    service.disconnect(landlord_id)  # idempotent
