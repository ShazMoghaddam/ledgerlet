"""One place to ask 'what time is it?'.

Always timezone-aware UTC. Services receive a clock function instead of calling
this directly, so tests can freeze time.
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)
