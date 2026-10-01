"""Repository against a real database: filters, ordering, constraints, enum round trip."""

from datetime import date
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.properties.models import Property
from app.modules.properties.repository import PropertyRepository
from app.modules.transactions.categories import TransactionCategory, TransactionSource
from app.modules.transactions.models import Transaction
from app.modules.transactions.repository import TransactionRepository


@pytest.fixture
def property_id(db_session: Session, landlord_id: UUID) -> UUID:
    prop = PropertyRepository(db_session).add(
        Property(
            landlord_id=landlord_id,
            nickname="Elm Court",
            address_line_1="2 Elm Court",
            town="London",
            postcode="SW1A 1AA",
        )
    )
    db_session.commit()
    return prop.id


@pytest.fixture
def repo(db_session: Session) -> TransactionRepository:
    return TransactionRepository(db_session)


def make(property_id: UUID, **overrides: object) -> Transaction:
    fields = {
        "property_id": property_id,
        "transaction_date": date(2026, 9, 1),
        "category": TransactionCategory.RENTAL_INCOME,
        "description": "Rent",
        "amount_pence": 85000,
    }
    return Transaction(**{**fields, **overrides})


def test_add_applies_defaults(repo, property_id) -> None:
    t = repo.add(make(property_id))
    repo.commit()
    assert t.id is not None
    assert t.source is TransactionSource.MANUAL
    assert t.locked_at is None


def test_enums_round_trip_through_the_database(repo, db_session, property_id) -> None:
    t = repo.add(make(property_id, category=TransactionCategory.RESIDENTIAL_FINANCE_COSTS))
    repo.commit()
    db_session.expire_all()  # force a fresh read from the database

    loaded = repo.get(t.id)
    assert loaded is not None
    assert loaded.category is TransactionCategory.RESIDENTIAL_FINANCE_COSTS

    stored = db_session.execute(
        text("SELECT category FROM transactions WHERE amount_pence = 85000")
    ).scalar_one()
    assert stored == "residential_finance_costs"


def test_list_filters_and_orders(repo, property_id) -> None:
    repo.add(make(property_id, transaction_date=date(2026, 9, 1), description="Sep"))
    repo.add(make(property_id, transaction_date=date(2026, 4, 1), description="Apr"))
    repo.add(
        make(
            property_id,
            transaction_date=date(2026, 7, 1),
            description="Jul",
            category=TransactionCategory.TRAVEL_COSTS,
        )
    )
    repo.commit()

    assert [t.description for t in repo.list_for_property(property_id)] == ["Apr", "Jul", "Sep"]
    window = repo.list_for_property(
        property_id, date_from=date(2026, 6, 1), date_to=date(2026, 9, 1)
    )
    assert [t.description for t in window] == ["Jul", "Sep"]
    travel = repo.list_for_property(property_id, category=TransactionCategory.TRAVEL_COSTS)
    assert [t.description for t in travel] == ["Jul"]


def test_delete(repo, property_id) -> None:
    t = repo.add(make(property_id))
    repo.commit()
    repo.delete(t)
    repo.commit()
    assert repo.get(t.id) is None


def test_database_rejects_non_positive_amount(repo, db_session, property_id) -> None:
    with pytest.raises(IntegrityError):
        repo.add(make(property_id, amount_pence=0))
    db_session.rollback()


def test_database_rejects_unknown_category(db_session, property_id) -> None:
    # Bypasses the ORM entirely: the CHECK constraint is the last line of defence.
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO transactions (id, property_id, transaction_date, category, "
                "description, amount_pence, source, created_at, updated_at) VALUES "
                "(:id, :pid, '2026-09-01', 'made_up', 'x', 100, 'manual', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": "00000000-0000-0000-0000-000000000001", "pid": str(property_id)},
        )
        db_session.flush()
    db_session.rollback()


def test_same_import_fingerprint_twice_in_a_property_is_rejected(
    repo, db_session, property_id
) -> None:
    repo.add(make(property_id, import_fingerprint="a" * 64))
    repo.commit()
    with pytest.raises(IntegrityError):
        repo.add(make(property_id, import_fingerprint="a" * 64, description="again"))
    db_session.rollback()


def test_many_manual_transactions_without_fingerprints_are_fine(repo, property_id) -> None:
    repo.add(make(property_id))
    repo.add(make(property_id))
    repo.commit()
    assert len(repo.list_for_property(property_id)) == 2
