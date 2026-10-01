"""Application settings, loaded from environment variables (or a .env file).

Every setting is prefixed with LEDGERLET_, e.g. LEDGERLET_DATABASE_URL.
Nothing else in the codebase reads os.environ directly: it asks for Settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LEDGERLET_", extra="ignore")

    app_name: str = "LedgerLet"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://ledgerlet:ledgerlet@localhost:5432/ledgerlet"
    sql_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
