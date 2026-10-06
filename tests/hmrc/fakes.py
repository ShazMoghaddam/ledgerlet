"""Stand-ins for HMRC and the connection table, so nothing in the suite touches HMRC."""

from uuid import UUID, uuid4

from cryptography.fernet import Fernet

from app.core.time import utc_now
from app.modules.hmrc.api import HmrcResponse
from app.modules.hmrc.models import HmrcConnection
from app.modules.hmrc.oauth import HmrcAuthError, TokenGrant
from app.modules.hmrc.service import HmrcNotConnectedError, OAuthSettings

TEST_TOKEN_KEY = Fernet.generate_key().decode()
# What the browser sends in X-LedgerLet-Device (shaped like the dev device page output).
TEST_DEVICE = {
    "device_id": "beec798b-b366-47fa-b1f8-92cead59b56e",
    "js_user_agent": "Mozilla/5.0 (Macintosh)",
    "screens": [{"width": 1512, "height": 982, "scaling_factor": 2, "colour_depth": 30}],
    "window_width": 1512,
    "window_height": 860,
    "utc_offset_minutes": 60,
}
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


class FakeHmrcApi:
    """Answers like HMRC's sandbox from canned bodies, and records every call made."""

    def __init__(self) -> None:
        self._make = HmrcResponse
        self.calls: list[dict] = []
        self.businesses: list[dict] = [
            {"typeOfBusiness": "uk-property", "businessId": "XPIS12345678901"},
            {"typeOfBusiness": "self-employment", "businessId": "XAIS12345678910"},
        ]
        self.obligation_details: list[dict] = [
            {
                "periodStartDate": "2026-04-06",
                "periodEndDate": "2026-07-05",
                "dueDate": "2026-08-07",
                "status": "fulfilled",
                "receivedDate": "2026-08-01",
            },
            {
                "periodStartDate": "2026-04-06",
                "periodEndDate": "2026-10-05",
                "dueDate": "2026-11-07",
                "status": "open",
            },
        ]
        self.fail_with: tuple[int, dict] | None = None
        self.extra_groups: list[dict] = []  # other businesses' obligations HMRC may include

    def get(self, path, version, access_token, fraud_headers, params=None, test_scenario=None):
        self.calls.append(
            {
                "path": path,
                "version": version,
                "token": access_token,
                "fraud_headers": dict(fraud_headers),
                "params": dict(params or {}),
                "test_scenario": test_scenario,
            }
        )
        if self.fail_with:
            status, body = self.fail_with
            return self._make(status, body, "corr-123")
        if path.endswith("/list"):
            return self._make(200, {"listOfBusinesses": self.businesses}, "corr-1")
        return self._make(
            200,
            {
                "obligations": [
                    {
                        "typeOfBusiness": "uk-property",
                        "businessId": "XPIS12345678901",
                        "obligationDetails": self.obligation_details,
                    },
                    *self.extra_groups,
                ]
            },
            "corr-2",
        )


class FakeTokens:
    def __init__(self, connected: bool = True) -> None:
        self.connected = connected

    def access_token(self, landlord_id: UUID) -> str:
        if not self.connected:
            raise HmrcNotConnectedError("Connect LedgerLet to HMRC first")
        return "live-access-token"


class FakeTaxpayerRepository:
    def __init__(self) -> None:
        self.items: dict = {}
        self.commit_count = 0

    def get_for_landlord(self, landlord_id):
        return self.items.get(landlord_id)

    def add(self, taxpayer):
        taxpayer.id = taxpayer.id or uuid4()
        self.items[taxpayer.landlord_id] = taxpayer
        return taxpayer

    def commit(self) -> None:
        self.commit_count += 1
