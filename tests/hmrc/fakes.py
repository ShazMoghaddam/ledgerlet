"""Stand-ins for HMRC and the connection table, so nothing in the suite touches HMRC."""

from uuid import UUID, uuid4

from cryptography.fernet import Fernet

from app.core.time import utc_now
from app.modules.hmrc.models import HmrcConnection
from app.modules.hmrc.oauth import HmrcAuthError, TokenGrant
from app.modules.hmrc.service import OAuthSettings

TEST_TOKEN_KEY = Fernet.generate_key().decode()
TEST_OAUTH_SETTINGS = OAuthSettings(
    authorize_url="https://test-www.tax.service.gov.uk/oauth/authorize",
    client_id="test-client-id",
    redirect_uri="http://localhost:8000/api/v1/hmrc/callback",
    scopes="read:self-assessment write:self-assessment",
)


class FakeOAuthClient:
    """Behaves like HMRC's token endpoint: each grant issues a fresh, numbered token pair."""

    def __init__(self) -> None:
        self.issued = 0
        self.valid_codes: set[str] = {"good-code"}
        self.live_refresh_tokens: set[str] = set()
        self.calls: list[tuple[str, str]] = []

    def _issue(self) -> TokenGrant:
        self.issued += 1
        refresh = f"refresh-{self.issued}"
        self.live_refresh_tokens.add(refresh)
        return TokenGrant(
            access_token=f"access-{self.issued}",
            refresh_token=refresh,
            expires_in=4 * 3600,
            scope="read:self-assessment write:self-assessment",
        )

    def exchange_code(self, code: str) -> TokenGrant:
        self.calls.append(("exchange", code))
        if code not in self.valid_codes:
            raise HmrcAuthError("invalid_grant")
        self.valid_codes.discard(code)  # codes are single-use
        return self._issue()

    def refresh(self, refresh_token: str) -> TokenGrant:
        self.calls.append(("refresh", refresh_token))
        if refresh_token not in self.live_refresh_tokens:
            raise HmrcAuthError("invalid_grant")
        self.live_refresh_tokens.discard(refresh_token)  # refresh tokens are single-use
        return self._issue()

    def application_token(self) -> str:
        return "app-token"


class FakeConnectionRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, HmrcConnection] = {}
        self.commit_count = 0

    def get_for_landlord(self, landlord_id: UUID) -> HmrcConnection | None:
        return self.items.get(landlord_id)

    def add(self, connection: HmrcConnection) -> HmrcConnection:
        connection.id = connection.id or uuid4()
        connection.created_at = connection.created_at or utc_now()
        connection.updated_at = connection.updated_at or utc_now()
        self.items[connection.landlord_id] = connection
        return connection

    def delete(self, connection: HmrcConnection) -> None:
        self.items.pop(connection.landlord_id, None)

    def commit(self) -> None:
        self.commit_count += 1


class FakeFraudValidator:
    """Records what would have been sent to HMRC and answers like a happy sandbox."""

    def __init__(self) -> None:
        self.received: list[dict[str, str]] = []

    def validate(self, headers: dict[str, str]) -> dict:
        self.received.append(dict(headers))
        return {"http_status": 200, "code": "VALID_HEADERS", "message": "All headers appear valid"}
