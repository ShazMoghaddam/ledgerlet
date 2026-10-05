from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.hmrc.models import HmrcConnection
from app.modules.hmrc.repository import HmrcConnectionRepository
from app.modules.landlords.models import Landlord

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def landlord(db_session: Session) -> Landlord:
    row = Landlord(auth_issuer="test", auth_subject=str(uuid4()))
    db_session.add(row)
    db_session.commit()
    return row


def connection(landlord_id) -> HmrcConnection:
    return HmrcConnection(
        landlord_id=landlord_id,
        access_token_encrypted="enc-a",
        refresh_token_encrypted="enc-r",
        access_token_expires_at=NOW,
        scope="read:self-assessment",
        connected_at=NOW,
    )


def test_add_get_delete(db_session: Session) -> None:
    repo = HmrcConnectionRepository(db_session)
    owner = landlord(db_session)
    repo.add(connection(owner.id))
    repo.commit()
    found = repo.get_for_landlord(owner.id)
    assert found is not None and found.access_token_encrypted == "enc-a"
    repo.delete(found)
    repo.commit()
    assert repo.get_for_landlord(owner.id) is None


def test_one_connection_per_landlord(db_session: Session) -> None:
    repo = HmrcConnectionRepository(db_session)
    owner = landlord(db_session)
    repo.add(connection(owner.id))
    repo.commit()
    with pytest.raises(IntegrityError):
        repo.add(connection(owner.id))
    db_session.rollback()
