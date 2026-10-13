"""Settings fill in what the host already knows, but never override what's set."""

from app.core.config import Settings


def test_a_hosts_postgres_url_gets_the_driver_named(monkeypatch) -> None:
    for given in ("postgres://u:p@db:5432/x", "postgresql://u:p@db:5432/x"):
        monkeypatch.setenv("LEDGERLET_DATABASE_URL", given)
        assert Settings(_env_file=None).database_url == "postgresql+psycopg://u:p@db:5432/x"
    monkeypatch.setenv("LEDGERLET_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    assert Settings(_env_file=None).database_url == "sqlite+pysqlite:///:memory:"


def test_on_render_the_public_address_is_where_hmrc_returns(monkeypatch) -> None:
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://ledgerlet.onrender.com/")
    s = Settings(_env_file=None)
    assert s.app_base_url == "https://ledgerlet.onrender.com"
    assert s.hmrc_redirect_uri == "https://ledgerlet.onrender.com/api/v1/hmrc/callback"


def test_explicit_addresses_win(monkeypatch) -> None:
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://ledgerlet.onrender.com")
    monkeypatch.setenv("LEDGERLET_APP_BASE_URL", "https://app.ledgerlet.co.uk")
    monkeypatch.setenv("LEDGERLET_HMRC_REDIRECT_URI", "https://app.ledgerlet.co.uk/cb")
    s = Settings(_env_file=None)
    assert (s.app_base_url, s.hmrc_redirect_uri) == (
        "https://app.ledgerlet.co.uk",
        "https://app.ledgerlet.co.uk/cb",
    )


def test_off_render_the_local_defaults_stay(monkeypatch) -> None:
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    s = Settings(_env_file=None)
    assert s.app_base_url == "http://localhost:5173"
    assert s.hmrc_redirect_uri == "http://localhost:8000/api/v1/hmrc/callback"
