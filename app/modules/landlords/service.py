"""Layer 2: rules for landlords."""

from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from app.core.auth import VerifiedIdentity
from app.core.exceptions import ConflictError
from app.modules.landlords.models import Landlord
from app.modules.landlords.schemas import LandlordUpdate


class LandlordRepositoryProtocol(Protocol):
    def find_by_identity(self, issuer: str, subject: str) -> Landlord | None: ...
    def add(self, landlord: Landlord) -> Landlord: ...
    def commit(self) -> None: ...


class LandlordService:
    def __init__(
        self,
        repository: LandlordRepositoryProtocol,
        sent_this_tax_year: Callable[[UUID], bool] = lambda _landlord_id: False,
    ) -> None:
        self._repo = repository
        # Has HMRC accepted an update from this landlord in the current tax year?
        self._sent_this_tax_year = sent_this_tax_year

    def sign_in(self, identity: VerifiedIdentity) -> Landlord:
        """Find the landlord for a verified identity, creating them on first sign-in.

        The email is refreshed from the token each time, since the provider owns it.
        """
        landlord = self._repo.find_by_identity(identity.issuer, identity.subject)
        if landlord is None:
            landlord = self._repo.add(
                Landlord(
                    auth_issuer=identity.issuer,
                    auth_subject=identity.subject,
                    email=identity.email,
                )
            )
            self._repo.commit()
        elif identity.email and landlord.email != identity.email:
            landlord.email = identity.email
            self._repo.commit()
        return landlord

    def update_profile(self, landlord: Landlord, data: LandlordUpdate) -> Landlord:
        """Rule: the update basis can't change once HMRC has an update for this tax year.

        Standard and calendar quarters end on different days, and HMRC needs every
        update in a year to reach the end date of the last one it accepted. Switching
        mid-year would leave updates that can never be sent.
        """
        changes = data.model_dump(exclude_unset=True)
        basis = changes.get("period_basis")
        if (
            basis is not None
            and basis != landlord.period_basis
            and self._sent_this_tax_year(landlord.id)
        ):
            raise ConflictError(
                "You've already sent HMRC an update this tax year, so your quarters "
                "can't change until the next tax year."
            )
        for field, value in changes.items():
            setattr(landlord, field, value)
        self._repo.commit()
        return landlord
