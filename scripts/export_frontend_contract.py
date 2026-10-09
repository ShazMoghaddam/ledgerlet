"""Write the API contract and sample responses the frontend is built and tested against.

    python -m scripts.export_frontend_contract

Writes, under frontend/:
    openapi.json                 the API description; `npm run api:types` turns it into types
    src/test/fixtures/*.json     real responses for the sample landlord (scripts/seed_demo.py)

The responses come from the real app: an in-memory database, the sample data, and
"today" fixed at 9 October 2026, so the figures match the design boards and tests
never depend on the date they run. CI runs this, regenerates the TypeScript types,
and fails if the types or fixtures change without being committed, so the frontend
can't drift from the backend.

HMRC responses aren't exported (they need HMRC); the frontend's own fixtures cover them.
"""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every table)
from app.core.database import Base, get_db
from app.main import create_app
from app.modules.landlords.dependencies import get_current_landlord
from app.modules.landlords.models import Landlord
from app.modules.properties.dependencies import PropertyServiceDep
from app.modules.properties.models import Property
from app.modules.tax.dependencies import get_tax_service
from app.modules.tax.service import TaxService
from app.modules.transactions.dependencies import TransactionServiceDep
from app.modules.transactions.models import Transaction
from scripts.seed_demo import DATA_TODAY, seed

ROOT = Path(__file__).resolve().parent.parent / "frontend"
FIXTURES = ROOT / "src" / "test" / "fixtures"
STAMP = datetime(2026, 10, 9, 9, 0, tzinfo=UTC)

# name -> (path, query). Each becomes src/test/fixtures/<name>.json.
RESPONSES: dict[str, tuple[str, dict[str, str | int]]] = {
    "me": ("/api/v1/me", {}),
    "properties": ("/api/v1/properties", {}),
    "obligations": ("/api/v1/tax/obligations", {"tax_year": 2026}),
    "summary-q1": ("/api/v1/tax/summary", {"tax_year": 2026, "quarter": 1}),
    "summary-q2": ("/api/v1/tax/summary", {"tax_year": 2026, "quarter": 2}),
    "summary-q3": ("/api/v1/tax/summary", {"tax_year": 2026, "quarter": 3}),
    "transactions-recent": ("/api/v1/transactions", {"limit": 5}),
    "transactions-page-1": ("/api/v1/transactions", {"limit": 50}),
    "categories": ("/api/v1/transactions/categories", {}),
}


def _fixed_today() -> date:
    return DATA_TODAY


def main() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(bind=engine, autoflush=False, expire_on_commit=False)
    landlord = seed(session, "https://example.invalid/fixtures", "sample")
    ids = _stabilise(session)

    def tax_service(properties: PropertyServiceDep, transactions: TransactionServiceDep):
        return TaxService(properties=properties, transactions=transactions, today=_fixed_today)

    api = create_app()
    api.dependency_overrides[get_db] = lambda: session
    api.dependency_overrides[get_current_landlord] = lambda: landlord
    api.dependency_overrides[get_tax_service] = tax_service

    ROOT.joinpath("openapi.json").write_text(json.dumps(api.openapi(), indent=2) + "\n")
    FIXTURES.mkdir(parents=True, exist_ok=True)
    with TestClient(api) as client:
        for name, (path, query) in RESPONSES.items():
            resp = client.get(path, params=query)
            resp.raise_for_status()
            text = json.dumps(resp.json(), indent=2) + "\n"
            FIXTURES.joinpath(f"{name}.json").write_text(_apply(text, ids))
    print(f"Wrote openapi.json and {len(RESPONSES)} fixtures under {ROOT}")


def _stabilise(session: Session) -> dict[str, str]:
    """Make re-runs byte-identical: fixed timestamps, and an id map to predictable ids.

    Rows keep their insertion order (timestamps a second apart), so lists that
    sort by creation time come out the same every time.
    """
    mapping: dict[str, str] = {}
    for prefix, model in enumerate((Landlord, Property, Transaction), start=1):
        rows = session.query(model).order_by(model.created_at).all()
        for n, row in enumerate(rows, start=1):
            row.created_at = row.updated_at = STAMP + timedelta(seconds=n)
            mapping[str(row.id)] = str(UUID(int=(prefix << 96) + n))
    session.commit()
    return mapping


def _apply(text: str, mapping: dict[str, str]) -> str:
    for old, new in mapping.items():
        text = text.replace(old, new)
    return text


if __name__ == "__main__":
    main()
