# GradScout Backend

## Local setup

```bash
pip install -r requirements.txt

# Requires a local Postgres. If you don't have one:
#   sudo apt install postgresql
#   sudo -u postgres createuser gradscout -P   # set password to match .env
#   sudo -u postgres createdb -O gradscout gradscout_dev

cp .env.example .env   # adjust DATABASE_URL if needed, and set a real JWT_SECRET_KEY

for f in migrations/*.sql; do psql -U gradscout -d gradscout_dev -f "$f"; done

pytest tests/ -v
```

## What's here so far (Phase 0 + Phase 1 + Phase 2)

- `app/dedup/` — the dedup engine: normalize → block → score → decide.
  Pure Python, no database dependency. Fully covered by `tests/test_dedup.py`.
- `app/models.py` — SQLAlchemy models mirroring `migrations/0001_initial_schema.sql`.
- `app/storage.py` — wires the dedup engine to real persistence. This is
  what the scheduler (Phase 5) will call for every scraped job.
- `app/scrapers/` — all 7 scrapers ported from the prototype (adzuna,
  reed, jooble, charityjob, acca, thirdsector, w4mpjobs), returning
  plain dicts instead of the old JobListing dataclass. Field renamed:
  `organisation` -> `company`, matching the dedup engine and schema.
- `app/pipeline.py` — orchestrates scrape -> dedup -> store across every
  enabled source, with per-source failure isolation. Run directly via
  `python -m app.pipeline` for a manual scrape.
- `migrations/` — numbered SQL files. Never edit an already-applied one
  once there's real data depending on it — write a new numbered
  migration instead (see 0003 for a worked example: it adds a source
  that was missing from 0002, rather than editing 0002 in place).

## Adding a new job source later

Because sources are configured as data (see `sources` table), adding an
8th source that fits an existing `scraper_type` (`static`, `rss`,
`adzuna`, `reed`, `jooble`) is just:

```sql
INSERT INTO sources (name, scraper_type, config) VALUES
('new-site-name', 'static', '{"url": "...", "parser": "parse_new_site"}');
```

No code deploy, no migration. A genuinely new *type* of source (a new
API with a different response shape) needs one new scraper class in
`app/scrapers/`, registered in `app/scrapers/registry.py`'s
`SCRAPER_TYPES` dict — that's the only case that does.

## Running the pipeline manually

```bash
export ADZUNA_APP_ID=... ADZUNA_APP_KEY=... REED_API_KEY=... JOOBLE_API_KEY=...
python -m app.pipeline
```

Scrapes every enabled source once, storing results through the dedup
engine, and prints a summary. This is what Phase 5's scheduler will
call on a timer — for now it's a manual, one-off run.

## Running the API (Phase 3)

```bash
uvicorn app.main:app --reload
```

Then visit **http://localhost:8000/docs** — this is FastAPI's
auto-generated interactive documentation, not something maintained by
hand. Every endpoint is listed, and you can send real requests to your
local database directly from that page.

**Auth is real** (see "Authentication" below): `POST /auth/signup` or
`POST /auth/login` gives you a bearer token. On the `/docs` page, click
the padlock icon and paste `Bearer <token>` in to authorize every other
request from that page.

### Trying the full flow yourself

1. `POST /auth/signup` — `{"email": "you@example.com", "password": "at-least-8-chars"}`, copy the returned `access_token`
2. Authorize using that token (padlock icon, or the `Authorization: Bearer <token>` header manually)
3. `POST /criteria` — save a search (try `{"keywords": ["graduate"], "locations": ["london"]}`)
4. `GET /feed` — see which jobs currently in your database match

If your database has no jobs yet, run the Phase 2 pipeline first:
`python -m app.pipeline` (needs real API keys for Adzuna/Reed/Jooble to
actually find anything — see `.env.example`).

## Deploying

Two accounts needed — Railway (backend + database) and, later, Vercel
(frontend — not needed yet). Earlier versions of this project also used
Supabase for the database and for authentication; that's gone now —
Railway hosts the Postgres instance itself via its own Postgres plugin,
and this API issues and verifies its own auth tokens (see `app/auth.py`
and `app/security.py`), so there's no second platform account this app
needs just to run. Quick reference:

1. Push this repo to GitHub, create a Railway project from it, and set
   the service's **root directory to `backend`**.
2. Add a **Postgres** plugin to the same Railway project (New →
   Database → Add PostgreSQL). This does **not** automatically wire
   anything into your backend service — Railway requires an explicit
   reference variable. On the backend service's Variables tab, add
   `DATABASE_URL` with value `${{Postgres.DATABASE_URL}}` (use your
   Postgres service's actual name if you renamed it from the default).
   Skipping this step is exactly how a stale or manually-pasted
   connection string ends up in `DATABASE_URL` instead — worth
   double-checking this variable's actual value if anything below ever
   fails with a database authentication error.
3. Run the migrations against that same database, in order, from your
   own machine. Use the Postgres service's own **public** connection
   string for this (its Variables tab — look for the one with a real
   external hostname like `*.proxy.rlwy.net`, not
   `postgres.railway.internal`, which only resolves from inside
   Railway's network):
   ```bash
   psql "<railway-postgres-public-connection-string>" -f migrations/0001_initial_schema.sql
   psql "<railway-postgres-public-connection-string>" -f migrations/0002_seed_sources.sql
   psql "<railway-postgres-public-connection-string>" -f migrations/0003_add_w4mpjobs_source.sql
   psql "<railway-postgres-public-connection-string>" -f migrations/0004_add_location_category.sql
   psql "<railway-postgres-public-connection-string>" -f migrations/0005_industry_category.sql
   psql "<railway-postgres-public-connection-string>" -f migrations/0006_self_hosted_auth.sql
   psql "<railway-postgres-public-connection-string>" -f migrations/0007_add_favourites.sql
   ```
4. Add the remaining Railway environment variables: `JWT_SECRET_KEY`
   (generate one with `openssl rand -hex 32` — this is what signs every
   access token this API issues, so treat it like a password) and the
   three scraper API keys (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`,
   `REED_API_KEY`, `JOOBLE_API_KEY`).
5. Railway builds automatically (`railway.json` in this folder tells it
   how) and gives you a public URL — visit `<that-url>/docs` to confirm
   it's alive.

## The scheduler (Phase 5)

Runs inside the same process as the API — no separate Railway service
needed. Starts automatically on app startup (see `app/main.py`'s
lifespan handler), runs once immediately, then every
`SCRAPE_INTERVAL_MINUTES` (default 20) thereafter.

Each cycle: scrape every enabled source → dedup → store (Phase 2's
`run_pipeline`) → for every user with active criteria, compute and save
any new matches (Phase 3's `compute_and_materialize_matches`, now
called by a timer as well as by the live `/feed` endpoint).

Failures are visible, not silent: per-source failures land in
`sources.last_scrape_error` (queryable in the database), and everything
prints to stdout, which Railway captures as logs — check **Deployments
→ [latest] → Logs** to watch cycles happen in real time.

To disable the scheduler (e.g. for local API poking without triggering
real scrapes): set `DISABLE_SCHEDULER=true`.

## Authentication

The `X-User-Id` stub is gone, and so is Supabase. Two endpoints handle
identity now, both in `app/routers/auth.py`:

```
POST /auth/signup   {"email": "...", "password": "..."}  -> 201, {access_token, user}
POST /auth/login    {"email": "...", "password": "..."}  -> 200, {access_token, user}
```

Send the returned `access_token` as `Authorization: Bearer <token>` on
every other request. Passwords are hashed with bcrypt
(`app/security.py`); tokens are this API's own JWTs, signed with
`JWT_SECRET_KEY` and valid for 30 days — there's no external identity
provider and no JWKS fetch involved anywhere in this flow.

**Requires `JWT_SECRET_KEY`** as an environment variable — generate one
with `openssl rand -hex 32` and treat it like any other credential.
Without it, every signup, login, and authenticated request fails with
a 500 rather than silently accepting forged tokens.

**Deliberately missing**, and worth knowing about before this goes past
a closed test group: there's no email verification step and no
password-reset flow. Both need a transactional email provider (Resend,
Postmark, etc.) to build properly, which is real setup work not worth
doing before a single real user depends on it — but it does mean a
tester who forgets their password today needs a direct database fix,
not a self-serve reset link.

**Low-risk timing**: the scheduler doesn't go through this auth layer
at all (it calls the pipeline and matching logic directly), so scraping
and dedup keep running uninterrupted regardless of anything above.
