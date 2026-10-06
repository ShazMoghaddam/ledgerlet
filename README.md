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

The `imports` and `tax` modules are the exception: they own no tables and work
only through the other modules' services.

Shared plumbing lives in `app/core/` (settings, DB session, domain errors,
the HTTP error mapping, and sign-in token verification).

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
| Provider-agnostic sign-in (standard OIDC JWTs, RS256 only) | Choosing or changing identity provider is configuration, not code |
| Landlord row created on first sign-in | No separate sign-up step; the provider owns passwords, resets and 2FA |
| Identity is issuer + subject | A user id is only unique within the provider that issued it |
| Every failed sign-in gets the same 401 | Telling an attacker why a forged token failed would help them |
| Dev stand-in provider (`scripts/dev_auth.py`) | Same code path as production; refused when environment is production |
| Data migration for pre-auth properties | The deferred foreign key is added without losing earlier data |
| Period basis is a saved landlord setting | Explicit query value still overrides it |
| HMRC tokens encrypted at rest (Fernet) | A copy of the database alone can't act on anyone's tax affairs |
| OAuth state sealed + bound to a browser cookie | HMRC's redirect back can't be forged, replayed or completed in another browser |
| HMRC callback needs no LedgerLet token | It's a browser redirect; trust comes from the sealed state and cookie instead |
| Tokens refreshed automatically, refresh token rotated | Access tokens last 4 hours; HMRC issues a new refresh token each time |
| A refused refresh removes the connection | A dead grant is useless; the landlord is asked to reconnect |
| HMRC client behind a Protocol | Tests and CI never call HMRC |
| Fraud headers as small pure formatters | HMRC rejects near-misses; each format is pinned by a test and easy to adjust |
| HMRC's validator is the judge of the headers | Third-party header lists go stale; HMRC's sandbox says exactly what's wrong |
| Headers we can't fill are omitted, never faked | A made-up value is worse than an honest gap the validator can flag |
| `X-Forwarded-For` trusted only behind our own proxy | Otherwise any client could claim any IP |
| NINO encrypted at rest, validated, only ever shown masked | It's a sensitive identifier; `OE****77A` is enough to recognise |
| HMRC identity kept apart from the HMRC connection | Losing a token shouldn't mean re-entering a NINO |
| HMRC endpoints and versions in one file | A path or version change at HMRC is a one-line fix |
| HMRC errors passed on with HMRC's reference (502) | The landlord or support can quote it to HMRC |
| Raw HMRC response returned alongside our parsed view | Our parsing can always be checked against HMRC's own words |
| `Gov-Test-Scenario` only ever sent to the sandbox | The client drops it for production, whatever the caller asks |
| "No obligations found" is an empty list, not an error | Nothing due is an answer; only real failures are errors |
| Obligations re-checked for our business and dates | Defence in depth, and the sandbox can't filter in DYNAMIC mode |
| Money stored as integer pence | Exact sums, no rounding errors; Decimal pounds only at the API edge |
| Categories mirror HMRC's MTD UK property headings | Quarterly submission is a straight sum per category |
| Residential finance costs kept as their own category | HMRC requires mortgage interest reported separately (tax credit, not a deduction) |
| Amounts always positive; direction comes from category | One source of truth for income vs expense |
| Full amounts recorded, ownership share applied later | Records match the bank; tax module applies the joint-ownership split |
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
| Tax periods are pure date logic | Off-by-one-day errors are the classic tax bug; every boundary is unit tested |
| Summaries are cumulative from the year start | Matches HMRC: each quarterly update replaces the previous one |
| Standard and calendar bases supported | HMRC allows either; the deadlines are the same |
| Share applied per property per category, rounded half up | A written, tested rounding rule makes totals reproducible |
| Mortgage interest excluded from expenses and profit | It is relieved as a tax credit, so it is reported separately |
| Archived properties still count for their periods | Selling a property mid-year doesn't remove its income |
| `ownership_percentage` is the tax share | Couples default to 50/50 unless HMRC has a Form 17 |
| Transactions lock at year-end final declaration | Quarterly updates are cumulative, so in-year corrections must stay possible |

## Open questions for an accountant

- Recording full bank amounts and deriving each joint owner's share, versus recording only the share
- Calendar basis: where transactions dated 1 to 5 April belong

## Open choices

- Which identity provider to use in production (decided with the frontend)

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

Sign-in for local development (a stand-in for a real identity provider):

```bash
python scripts/dev_auth.py init        # once; paste the printed lines into .env
python scripts/dev_auth.py token --sub alice --email alice@example.com
```

API docs: http://127.0.0.1:8000/docs. Click **Authorize** and paste the token.

## HMRC sandbox (local development)

1. Register at the HMRC Developer Hub, create a sandbox application, and subscribe it to
   Property Business (MTD) 6.0, Obligations (MTD) 3.0, Business Details (MTD) 2.0,
   Create Test User 1.0 and Test Fraud Prevention Headers 1.0.
2. Add the redirect URI `http://localhost:8000/api/v1/hmrc/callback`.
3. Put `LEDGERLET_HMRC_CLIENT_ID`, `LEDGERLET_HMRC_CLIENT_SECRET` and `LEDGERLET_HMRC_TOKEN_KEY`
   in `.env` (see `.env.example`).
4. `python scripts/hmrc_test_user.py` creates a sandbox individual to sign in to HMRC as.
5. After connecting and saving the NINO, `python scripts/hmrc_create_property_business.py --sub <you>`
   gives that individual a UK property business (needs Self Assessment Test Support (MTD) 1.0).
   HMRC deletes sandbox test businesses after 7 days; re-run it when discovery stops finding one.
6. Set `LEDGERLET_HMRC_OBLIGATIONS_TEST_SCENARIO=DYNAMIC`. The sandbox's obligations aren't linked
   to businesses you create: it only generates them, unfiltered, for its own example businesses.
   `scripts/hmrc_probe_obligations.py` shows what each request variant returns.

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
   - 2b. CSV bank-statement import: preview, dedup, confirm (done)
   - Later: bank presets, auto-categorisation rules, one statement across several properties, refunds
3. Tax module: tax years, cumulative update periods, deadlines, year-to-date totals (done)
4. Auth + landlords: provider-agnostic sign-in, landlord settings (done)
5. HMRC MTD submission, sandbox first
   - 5a-i. Connect to HMRC: OAuth, encrypted tokens, refresh (done)
   - 5a-ii. Fraud prevention headers, validated by HMRC's test API (done)
   - 5b-i. NINO, business discovery, obligations (read-only) (this phase)
   - 5b-ii. Cumulative quarterly submission and audit trail
   - Later: Gov-Client-Multi-Factor (with the chosen identity provider), Gov-Vendor-License-IDs
6. React + Vite frontend
7. Open banking as a second transaction source
