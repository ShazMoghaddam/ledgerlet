"""Application settings, loaded from environment variables (or a .env file).

Every setting is prefixed with LEDGERLET_, e.g. LEDGERLET_DATABASE_URL.
Nothing else in the codebase reads os.environ directly: it asks for Settings.
"""

from functools import lru_cache
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LEDGERLET_", extra="ignore")

    app_name: str = "LedgerLet"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://ledgerlet:ledgerlet@localhost:5432/ledgerlet"
    sql_echo: bool = False

    # Authentication (any OpenID Connect provider). Give the JWKS URL in production;
    # the JWKS file is only for local development with scripts/dev_auth.py.
    auth_issuer: str | None = None
    auth_audience: str = "ledgerlet-api"
    auth_jwks_url: str | None = None
    auth_jwks_file: str | None = None

    # HMRC (Making Tax Digital). Defaults point at HMRC's sandbox.
    hmrc_base_url: str = "https://test-api.service.hmrc.gov.uk"
    hmrc_authorize_url: str = "https://test-www.tax.service.gov.uk/oauth/authorize"
    hmrc_client_id: str | None = None
    hmrc_client_secret: str | None = None
    hmrc_redirect_uri: str = "http://localhost:8000/api/v1/hmrc/callback"
    hmrc_scopes: str = "read:self-assessment write:self-assessment"
    hmrc_token_key: str | None = None  # Fernet key: encrypts HMRC tokens at rest

    # Fraud prevention headers. Our server's public IP (unknown on a laptop; set in
    # production). Trust X-Forwarded-For only when running behind our own proxy.
    hmrc_vendor_public_ip: str | None = None

    # Sandbox only: Gov-Test-Scenario for the obligations call (e.g. STATEFUL). Ignored in
    # production. Business discovery always asks the sandbox for STATEFUL data.
    hmrc_obligations_test_scenario: str | None = None
    trust_proxy_headers: bool = False

    @model_validator(mode="after")
    def _no_dev_keys_in_production(self) -> Self:
        if self.environment == "production" and self.auth_jwks_file:
            raise ValueError("auth_jwks_file is for local development only")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
