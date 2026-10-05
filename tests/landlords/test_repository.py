import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.landlords.models import Landlord
from app.modules.landlords.repository import LandlordRepository
from app.modules.tax.periods import PeriodBasis


def test_find_by_identity(db_session: Session) -> None:
    repo = LandlordRepository(db_session)
    repo.add(Landlord(auth_issuer="https://idp", auth_subject="user-1"))
    repo.commit()
    found = repo.find_by_identity("https://idp", "user-1")
    assert found is not None
    assert found.period_basis is PeriodBasis.STANDARD
    assert repo.find_by_identity("https://other", "user-1") is None


def test_identity_is_unique(db_session: Session) -> None:
    repo = LandlordRepository(db_session)
    repo.add(Landlord(auth_issuer="https://idp", auth_subject="user-1"))
    repo.commit()
    with pytest.raises(IntegrityError):
        repo.add(Landlord(auth_issuer="https://idp", auth_subject="user-1"))
    db_session.rollback()
