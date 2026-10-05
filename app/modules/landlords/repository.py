"""Layer 3: SQL for landlords."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.landlords.models import Landlord


class LandlordRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_identity(self, issuer: str, subject: str) -> Landlord | None:
        stmt = select(Landlord).where(
            Landlord.auth_issuer == issuer, Landlord.auth_subject == subject
        )
        return self._session.scalars(stmt).one_or_none()

    def add(self, landlord: Landlord) -> Landlord:
        self._session.add(landlord)
        self._session.flush()
        return landlord

    def commit(self) -> None:
        self._session.commit()
