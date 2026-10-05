"""Shared fixtures.

Default: an in-memory SQLite database, so `pytest` works with zero setup.
Set LEDGERLET_TEST_DATABASE_URL to run the exact same suite against Postgres
(do this before closing each phase: Postgres is what production runs).
"""

import os
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers tables)
from app.core.auth import get_token_verifier
from app.core.database import Base, get_db
from app.main import create_app
from tests.auth import make_verifier

TEST_DATABASE_URL = os.getenv("LEDGERLET_TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")

if not TEST_DATABASE_URL.startswith("sqlite") and "test" not in TEST_DATABASE_URL:
    pytest.exit(
        "Refusing to run: LEDGERLET_TEST_DATABASE_URL must point at a database whose name "
        "contains 'test', because the suite drops every table.",
        returncode=2,
    )


@pytest.fixture
def engine() -> Iterator[Engine]:
    """A fresh schema per test, so tests can never leak state into each other."""
    if TEST_DATABASE_URL.startswith("sqlite"):
        eng = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    session = Session(bind=engine, autoflush=False, expire_on_commit=False)
    yield session
    session.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    # Real token verification, against the test identity provider's key.
    app.dependency_overrides[get_token_verifier] = make_verifier
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def landlord_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_landlord_id() -> UUID:
    return uuid4()
