"""Layer 2: rules for landlords."""

from typing import Protocol

from app.core.auth import VerifiedIdentity
from app.modules.landlords.models import Landlord
from app.modules.landlords.schemas import LandlordUpdate


class LandlordRepositoryProtocol(Protocol):
    def find_by_identity(self, issuer: str, subject: str) -> Landlord | None: ...
    def add(self, landlord: Landlord) -> Landlord: ...
    def commit(self) -> None: ...


class LandlordService:
    def __init__(self, repository: LandlordRepositoryProtocol) -> None:
        self._repo = repository

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
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(landlord, field, value)
        self._repo.commit()
        return landlord
