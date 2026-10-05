from uuid import uuid4

from app.core.time import utc_now
from app.modules.landlords.models import Landlord
from app.modules.tax.periods import PeriodBasis


class FakeLandlordRepository:
    def __init__(self) -> None:
        self.items: list[Landlord] = []
        self.commit_count = 0

    def find_by_identity(self, issuer: str, subject: str) -> Landlord | None:
        return next(
            (x for x in self.items if (x.auth_issuer, x.auth_subject) == (issuer, subject)), None
        )

    def add(self, landlord: Landlord) -> Landlord:
        landlord.id = landlord.id or uuid4()
        landlord.period_basis = landlord.period_basis or PeriodBasis.STANDARD
        landlord.created_at = landlord.created_at or utc_now()
        landlord.updated_at = landlord.updated_at or utc_now()
        self.items.append(landlord)
        return landlord

    def commit(self) -> None:
        self.commit_count += 1
