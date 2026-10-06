"""Domain errors raised by the service layer.

These deliberately know nothing about HTTP. The API layer translates them into
status codes in app/core/error_handlers.py. That keeps business logic usable
from anywhere: a web request, a CLI script, a background job, or a test.
"""


class DomainError(Exception):
    """Base class for expected, user-facing business errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """The thing doesn't exist, or it isn't yours (we never reveal which)."""


class ConflictError(DomainError):
    """The request clashes with current state, e.g. a duplicate or an archived record."""


class UpstreamError(DomainError):
    """An outside service (such as HMRC) refused or failed. Its own message is passed on."""


class BusinessRuleError(DomainError):
    """Well-formed input that breaks a rule needing context, e.g. a future-dated transaction."""
