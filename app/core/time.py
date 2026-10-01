"""One place to ask 'what time is it?' and 'what day is it?'.

Services receive these as injectable functions so tests can freeze time.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

UK_TZ = ZoneInfo("Europe/London")


def utc_now() -> datetime:
    """Timestamps (created_at, archived_at...) are always stored in UTC."""
    return datetime.now(UTC)


def uk_today() -> date:
    """Today's date as a UK landlord sees it.

    Business dates must use UK time: at 00:30 in summer (BST) it's already
    tomorrow in London but still yesterday in UTC.
    """
    return datetime.now(UK_TZ).date()
