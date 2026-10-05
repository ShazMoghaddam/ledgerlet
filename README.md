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

The `imports` module is the exception: it owns no tables and works only through
the other modules' services.

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
| Money stored as integer pence | Exact sums, no rounding errors; Decimal pounds only at the API edge |
| Categories mirror HMRC's MTD UK property headings | Quarterly submission is a straight sum per category |
| Residential finance costs kept as their own category | HMRC requires mortgage interest reported separately (tax credit, not a deduction) |
| Amounts always positive; direction comes from category | One source of truth for income vs expense |
| Full amounts recorded, ownership share applied later | Records match the bank; tax module applies the joint-ownership split |
| Locked transactions after HMRC submission | Corrections become new entries, never silent edits |
| `source` on every transaction | Manual, CSV and open banking are interchangeable ways in |
| Modules talk via services, not each other's tables | Transactions asks PropertyService about ownership; boundaries stay clean |
| UK date for business rules (`Europe/London`) | "Today" for a landlord is a UK date, not a UTC one |
| Migrations hard-code enum values | A migration is a frozen snapshot of what it created |
| Two-step CSV import, stateless preview | Nothing is saved until the landlord confirms; no staging table to clean up |
| Row fingerprint (sha256) + unique constraint | The same bank row can never be imported twice, enforced by the database |
| Occurrence number in the fingerprint | Two genuinely identical rows in one statement stay distinct, and still dedup on re-import |
| "Possible duplicate" flag on same date + amount | Catches a manual entry that the bank row would double, without blocking it |
| Generic column mapping, no bank presets yet | Presets will be built from real, checked exports rather than guessed |
| Bad rows reported, not fatal | One malformed line shouldn't sink a 300-row statement |
| Imports module owns no tables | It works only through the properties and transactions services |

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
GitHub Actions (`.github/workflows/ci.yml`) runs the same gate on every push.

## Roadmap

1. Properties module (done)
2. Transactions module
   - 2a. Core: manual entry, HMRC categories, integer pence, locking (done)
   - 2b. CSV bank-statement import: preview, dedup, confirm (this phase)
   - Later: bank presets, auto-categorisation rules, one statement across several properties, refunds
3. Tax module: tax years, quarterly periods, totals
4. Auth + landlords: replaces the header stand-in
5. HMRC MTD submission module (sandbox first)
6. React + Vite frontend
7. Open banking as a second transaction source
