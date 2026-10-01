from datetime import date

from app.core.time import uk_today, utc_now


def test_utc_now_is_timezone_aware() -> None:
    assert utc_now().tzinfo is not None


def test_uk_today_is_a_date() -> None:
    assert isinstance(uk_today(), date)
