import pytest

from app.core.auth import VerifiedIdentity
from app.core.exceptions import ConflictError
from app.modules.landlords.schemas import LandlordUpdate
from app.modules.landlords.service import LandlordService
from app.modules.tax.periods import PeriodBasis
from tests.landlords.fakes import FakeLandlordRepository


@pytest.fixture
def repo() -> FakeLandlordRepository:
    return FakeLandlordRepository()


@pytest.fixture
def service(repo) -> LandlordService:
    return LandlordService(repo)


def identity(subject="user-1", email="a@example.com", issuer="https://idp") -> VerifiedIdentity:
    return VerifiedIdentity(issuer=issuer, subject=subject, email=email)


def test_first_sign_in_creates_the_landlord(service, repo) -> None:
    landlord = service.sign_in(identity())
    assert len(repo.items) == 1
    assert landlord.email == "a@example.com"
    assert landlord.period_basis is PeriodBasis.STANDARD


def test_next_sign_in_finds_the_same_landlord(service, repo) -> None:
    first = service.sign_in(identity())
    commits = repo.commit_count
    assert service.sign_in(identity()).id == first.id
    assert len(repo.items) == 1
    assert repo.commit_count == commits  # nothing changed, nothing written


def test_email_follows_the_provider(service) -> None:
    service.sign_in(identity(email="old@example.com"))
    assert service.sign_in(identity(email="new@example.com")).email == "new@example.com"


def test_same_subject_at_different_issuers_are_different_people(service, repo) -> None:
    a = service.sign_in(identity(issuer="https://idp-a"))
    b = service.sign_in(identity(issuer="https://idp-b"))
    assert a.id != b.id


def test_update_profile(service) -> None:
    landlord = service.sign_in(identity())
    updated = service.update_profile(
        landlord, LandlordUpdate(display_name="Shaz", period_basis=PeriodBasis.CALENDAR)
    )
    assert (updated.display_name, updated.period_basis) == ("Shaz", PeriodBasis.CALENDAR)


def test_basis_can_change_before_anything_is_sent(repo) -> None:
    service = LandlordService(repo, sent_this_tax_year=lambda _id: False)
    landlord = service.sign_in(identity())
    service.update_profile(landlord, LandlordUpdate(period_basis=PeriodBasis.CALENDAR))
    assert landlord.period_basis is PeriodBasis.CALENDAR


def test_basis_is_fixed_once_hmrc_has_an_update_this_year(repo) -> None:
    service = LandlordService(repo, sent_this_tax_year=lambda _id: True)
    landlord = service.sign_in(identity())
    with pytest.raises(ConflictError, match="can't change until the next tax year"):
        service.update_profile(landlord, LandlordUpdate(period_basis=PeriodBasis.CALENDAR))
    assert landlord.period_basis is PeriodBasis.STANDARD
    # Other settings, and "changing" to the same basis, are still fine.
    service.update_profile(
        landlord, LandlordUpdate(display_name="Shaz", period_basis=PeriodBasis.STANDARD)
    )
    assert landlord.display_name == "Shaz"
