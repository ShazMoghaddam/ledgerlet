# LedgerLet

Making Tax Digital platform for UK landlords. Working name, pending a UK IPO
trademark and Companies House check.

Built in London by [Shaz Moghaddam](https://shazmoghaddam.github.io/).
Live demo, on HMRC's sandbox: [ledgerlet.onrender.com](https://ledgerlet.onrender.com)

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
| Category to HMRC field mapping in one table | If HMRC renames a field, it's a one-line fix; a test proves every category has a home |
| Preview uses the same totals as the tax summary | What the landlord sees is exactly what gets sent |
| All fields sent, zeros included | Each cumulative update replaces the last, so a figure that falls to zero must say so |
| Consolidated expenses refused at £90,000+ income | HMRC's threshold, enforced before anything is sent |
| A quarter can only be submitted after it ends | Updates are cumulative to a quarter end |
| No update may end earlier than one HMRC accepted | HMRC's rule; corrections go in a resubmission of the same or a later quarter |
| Append-only audit trail, written before success or failure returns | Every filing can be traced: what was sent, when, HMRC's reply and reference |
| Audit rows hold no NINO; landlord delete is RESTRICTed | Less sensitive data at rest, and filing history outlives everything else |
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
| One cross-property transaction list, newest first, paged | A landlord reads money like a bank statement, not one property at a time |
| List totals cover every match, at share, rounded per property per category | Same rule as the tax figures, so the list and the tax page always agree |
| Search text that looks like an amount also matches amounts | Landlords look for "96" as often as "boiler" |
| HMRC callback sends the browser back into the app | The landlord lands where they started, not on a page of JSON |
| Only an app path is accepted as the return page, sealed in the state | The callback can't be used to bounce someone to another site |
| Callback failures travel as short codes, never as text | Nobody can craft a link that makes LedgerLet display words of their choosing |
| Sample data script mirrors the design boards, pinned by a test | Designs, demo and frontend tests all show the same, correct figures |

## Open questions for an accountant

- Recording full bank amounts and deriving each joint owner's share, versus recording only the share
- Calendar basis: where transactions dated 1 to 5 April belong

## Open choices

- Hosting for production (Render for the demo)

## Dependencies

`pyproject.toml` says which packages LedgerLet needs and the oldest versions it works
with. `requirements.lock` (to run it) and `requirements-dev.lock` (to develop and test)
pin the exact version of every package, including indirect ones, so every install, CI
run and deployment uses the same code. To update them, deliberately:

```bash
uv pip compile pyproject.toml --universal --python-version 3.11 -o requirements.lock
uv pip compile pyproject.toml --extra dev --universal --python-version 3.11 -o requirements-dev.lock
pip install -r requirements-dev.lock && python -m pytest
```

Then regenerate the frontend contract (see below) and commit everything together.

## Running locally (macOS)

Needs Python 3.11+ and Docker Desktop.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.lock   # exact versions, the same as CI
pip install -e . --no-deps

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

Sample data (two properties and 29 transactions, the figures the designs use):

```bash
python scripts/seed_demo.py --sub alice
```

To try importing, `scripts/samples/oak-road-statement.csv` is a small Oak Road bank statement with
new rows, two possible duplicates of the sample data and one row that can't be read.

## Web app (local development)

Needs Node 20.19 or newer (`brew install node`). Run the API as above, then in a second tab:

```bash
cd frontend
npm install          # once
npm run dev          # http://localhost:5173
```

Sign in by pasting a token from `python scripts/dev_auth.py token --sub alice`. The dev server
forwards `/api` to the API on port 8000, so the browser sees one site, as it will in production.

```bash
npm test             # unit and component tests (fast, no browser)
npx playwright install chromium   # once
npm run test:e2e     # the built app in Chromium at phone, tablet and laptop sizes, with axe
npm run lint && npm run typecheck && npm run format:check
```

If you change the API, regenerate what the frontend is built against, then commit it:

```bash
python -m scripts.export_frontend_contract   # openapi.json and test fixtures
cd frontend && npm run api:types              # TypeScript types from openapi.json
```

### Frontend decisions

| Decision | Why |
|---|---|
| React + TypeScript, built with Vite; no Next.js | FastAPI is already the server and a signed-in app needs no server rendering |
| Pinned to the previous major versions (React Router 7, Vite 7, TypeScript 5.9) | Mature and well documented; upgrades get their own PR |
| Types generated from the API's OpenAPI description | A backend change the frontend doesn't handle fails the type check, not the browser |
| Test fixtures exported from the real API with the sample data | Tests see exactly what the app will see; CI fails if they drift |
| TanStack Query for everything from the server; no global store | Server data is the app's state; caching and refetching come for free |
| Money handled as whole pence parsed from strings | No floating point anywhere near an amount; `parseFloat` is banned by lint |
| Dates as calendar days in UTC; "today" is today in the UK | A day never shifts with the device's time zone; tax rules use UK dates |
| Hand-built components, CSS modules and design tokens | The look is LedgerLet's own, not a component library's |
| Native date, select and dialog controls; no widget library | Phones get their own pickers, screen readers know them, and nothing stores money as a JavaScript number (why React Aria's number field was dropped) |
| Amounts typed as text and converted straight to pence | "£1,200.50", "96" and "96.5" all work; mistakes get a plain-English message |
| All of a form's problems listed at the top, each linked to its field | Nobody hunts for what's wrong; screen readers hear the list first |
| List filters, search and page live in the URL | A filtered list survives refresh, Back, bookmarks and sharing |
| Transaction detail: a panel on laptops, its own page below that | Context stays on wide screens; a phone gets the whole screen |
| The API works out each row's share; the frontend never does sums on money | One rounding rule, tested once, in one place |
| Import shows the landlord's own columns and guesses the mapping | Every bank names columns differently; a guess they can see and change beats a preset list |
| Every row in the file is shown, including ones that won't import | Nothing disappears silently; unreadable rows say why |
| New rows start ticked, possible duplicates unticked | The safe default; a genuine second payment is one tick away |
| Categories suggested from the same description last time, exact match only | Predictable beats clever when the result goes to HMRC; the landlord still confirms each row |
| Import steps held in the page, not the URL | A chosen file can't survive a reload, so a reload honestly starts again |
| One navigation, three layouts: tab bar, rail, sidebar | Each screen size gets a fitting pattern; one set of links to maintain |
| Some components render different structures by width (table vs list) | A phone gets a signed list, not a squeezed table |
| Quarter state worked out from deadlines plus HMRC history | Updates are cumulative, so a later accepted update also covers earlier quarters |
| Focus moves to the new page's heading after navigating | Screen reader users hear the page change; Tab starts at the top |
| Sign-in token in sessionStorage, behind one small module | Gone when the tab closes; swapping in the identity provider touches one file |
| Signing out clears every cached response | The next person on the device sees nothing of the last |
| Browser tests at 390, 834 and 1440 px with axe | Responsive layout, tap targets and accessibility are checked, not assumed |

## Sign-in with Auth0

LedgerLet checks standard signed tokens (see `app/core/auth.py`), so Auth0 is set up
in Auth0's dashboard and in settings; no code changes. One-time setup:

1. **Create a tenant** in Auth0 and choose the **UK** region (the privacy notice says
   sign-in data is held there).
2. **Create an API** (Applications › APIs): name `LedgerLet API`, identifier
   `https://api.ledgerlet.app`, signing algorithm RS256. The identifier is the audience.
   In the API's **Settings › Access Settings**, turn on **Allow Skipping User
   Consent**, so landlords aren't asked to approve LedgerLet's access to its own API.
   Don't use Auth0's Management API (`…/api/v2/`) for any of this.
3. **Create an application** (Applications › Applications), type *Single Page
   Application*. In its settings add, for local development and for each deployed
   address:
   - Allowed Callback URLs: `http://localhost:5173/sign-in/callback`
   - Allowed Logout URLs: `http://localhost:5173/sign-in`
   - Allowed Web Origins: `http://localhost:5173`
   - Refresh Token Rotation: on.

   Then let the application call the API: in the LedgerLet API, open **Application
   Access**, find the application, and under **User-Delegated Access** choose
   **Grant Access**. Without it, sign-in ends with "Client not authorized".
4. **Add the email to access tokens** (Actions › Library › Create Action, trigger
   *Post Login*), then add it to the Login flow:

   ```js
   exports.onExecutePostLogin = async (event, api) => {
     api.accessToken.setCustomClaim("https://ledgerlet.app/email", event.user.email);
   };
   ```
5. **Settings.** Backend `.env`:

   ```
   LEDGERLET_AUTH_ISSUER=https://YOUR-TENANT.uk.auth0.com/
   LEDGERLET_AUTH_AUDIENCE=https://api.ledgerlet.app
   LEDGERLET_AUTH_JWKS_URL=https://YOUR-TENANT.uk.auth0.com/.well-known/jwks.json
   LEDGERLET_AUTH_EMAIL_CLAIM=https://ledgerlet.app/email
   ```

   (Remove `LEDGERLET_AUTH_JWKS_FILE`. The issuer ends with a `/`, as Auth0 writes it.)
   Frontend `frontend/.env.local` (see `frontend/.env.example`): the tenant domain, the
   application's client ID and the API identifier.

Without the frontend settings, the sign-in page keeps the development token box, so
tests and local work don't need Auth0. A landlord who signed in with a development
token is a different landlord from the same person through Auth0 (a different issuer).

## Deploying to Render (demo)

Production is one Docker image (`Dockerfile`): the web app is built, then served by
the API from the same address, so there's no CORS and HMRC's sign-in cookie works.
On start it applies any new migrations (`docker/start.sh`). CI builds the same image
and checks it runs. `render.yaml` describes the Render setup.

1. **Auth0 first** (see above). Add the Render address to the application's
   Allowed Callback URLs (`https://ledgerlet.onrender.com/sign-in/callback`), Logout
   URLs (`https://ledgerlet.onrender.com/sign-in`) and Web Origins
   (`https://ledgerlet.onrender.com`). If Render gives the service a different
   address, use that instead.
2. **HMRC Developer Hub:** add `https://ledgerlet.onrender.com/api/v1/hmrc/callback`
   to your sandbox application's redirect URIs.
3. **Render:** New > Blueprint, connect the GitHub repo, and fill in the values it
   asks for: the Auth0 issuer, JWKS URL, domain and client ID; the HMRC client ID and
   secret; and a **new** HMRC token key:

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
4. Render builds and deploys. After that, every merge to `main` deploys once CI
   passes.

The app's public address and HMRC's redirect URI are taken from Render's
`RENDER_EXTERNAL_URL`; set `LEDGERLET_APP_BASE_URL` and `LEDGERLET_HMRC_REDIRECT_URI`
only for a custom domain.

The free plans are for a demo: the service sleeps after 15 minutes idle (about a
minute to wake), and the free database is deleted 30 days after it's created. Move
both to paid plans before anyone relies on it.

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

A phase is done when all four commands above pass, on SQLite **and** Postgres, and the
frontend's checks pass. GitHub Actions (`.github/workflows/ci.yml`) runs the same gate on every
push: the backend job, a frontend job (lint, formatting, types, unit tests, build, browser
tests), and a contract job that regenerates the frontend's API types and test fixtures from the
backend and fails if they've changed without being committed.

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
   - 5b-i. NINO, business discovery, obligations (read-only) (done)
   - 5b-ii. Cumulative quarterly submission and audit trail (done)
   - Later: year-end final declaration (and year-end transaction locking), encryption key rotation
   - Later: Gov-Client-Multi-Factor (with the chosen identity provider), Gov-Vendor-License-IDs
6. React + Vite frontend
   - 6a. API for the frontend: cross-property transactions, HMRC return to the app, sample data (done)
   - 6b. Frontend foundation: design tokens, app shell and navigation at every screen size, Overview (done)
   - 6c-i. Transactions: list, filters, detail, add, edit, delete (done)
   - 6c-ii. CSV import (done)
   - 6c-iii. Tax year and quarter pages (done)
   - 6c-iv. Review and submit to HMRC, and the HMRC connection page (done)
   - 6d. Properties, Settings, privacy notice and terms (done)
7. Real sign-in (Auth0, UK region) and the Render demo, end to end on HMRC's sandbox (done)
8. Before real landlords: Google sign-in keys of our own, ICO registration, HMRC production access
9. Open banking as a second transaction source

## Author

**Shaz Moghaddam**, London, UK

[shazmoghaddam.github.io](https://shazmoghaddam.github.io/) ·
[LinkedIn](https://www.linkedin.com/in/shazmoghaddam) ·
[GitHub](https://github.com/ShazMoghaddam)

## Licence

Copyright © 2026 Shaz Moghaddam. All rights reserved. This is proprietary software,
not open source: see [LICENSE](LICENSE).
