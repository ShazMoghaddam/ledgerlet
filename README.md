# LedgerLet

Making Tax Digital platform for UK landlords. Working name, pending a UK IPO
trademark and Companies House check.

## Architecture

A **modular monolith**: one deployable FastAPI app, organised by business
domain. Each module (`app/modules/<name>/`) owns its own four layers:

```
HTTP request
   |
router.py       API layer         speaks HTTP, validates shape, calls one service method
   |
service.py      Service layer     business rules; no HTTP, no SQL
   |
repository.py   Repository layer  the only place that queries the database
   |
models.py       Data model        SQLAlchemy table definition
```

Rule: each layer only talks to the one directly below it.

Shared plumbing lives in `app/core/` (settings, DB session, domain errors,
the HTTP error mapping, and the current-landlord dependency).

## Key design decisions

| Decision | Why |
|---|---|
| Modular monolith, not microservices | One person can run it; module boundaries keep it clean |
| FastAPI + Pydantic | Request validation and API docs for free; data correctness matters in tax |
| PostgreSQL + SQLAlchemy 2.0 + Alembic | Integrity for financial data; versioned, reviewable schema changes |
| Sync endpoints (for now) | Simpler and plenty fast at this scale; can move to async later |
| Service depends on a repository *Protocol* | Business rules are tested with an in-memory fake, no DB |
| Domain errors, not HTTPException, in services | Logic stays reusable from CLI, jobs and tests |
| 404 for other landlords' data | Never reveal that someone else's record exists |
| Archive, never delete, properties | Financial history must survive for HMRC enquiries |
| Ownership percentage on property | Jointly owned property is common and tax splits by share |
| Model for portfolio, launch for one property | No rewrite needed as landlords grow |
| `X-Landlord-Id` header | Temporary stand-in for auth; only `app/core/security.py` changes later |

## Running locally (macOS)

Needs Python 3.11+ and Docker Desktop.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
docker compose up -d db
alembic upgrade head

uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs (add an `X-Landlord-Id` header with any UUID,
e.g. from `uuidgen`).

## Testing

```bash
pytest                       # fast, in-memory SQLite
LEDGERLET_TEST_DATABASE_URL=postgresql+psycopg://ledgerlet:ledgerlet@localhost:5432/ledgerlet_test pytest
alembic check                # confirms models and migrations agree
ruff check .
```

The test database must contain `test` in its name; the suite drops all tables.
`ledgerlet_test` is created automatically the first time the Docker volume is
created. If your volume already existed, create it once with:
`docker compose exec db createdb -U ledgerlet ledgerlet_test`

## Phase gate

A phase is done when all four commands above pass, on SQLite **and** Postgres.

## Roadmap

1. Properties module (this phase)
2. Transactions module: income/expenses per property, HMRC categories, manual entry + CSV import behind a source interface
3. Tax module: tax years, quarterly periods, totals
4. Auth + landlords: replaces the header stand-in
5. HMRC MTD submission module (sandbox first)
6. React + Vite frontend
7. Open banking as a second transaction source
