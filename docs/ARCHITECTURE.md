# DiraScan Architecture

This document describes how DiraScan is put together: the services, the scrape
job lifecycle, the data model, and the invariants that keep it working. For a
quick start see [`../README.md`](../README.md); for AI-assistant conventions see
[`../CLAUDE.md`](../CLAUDE.md).

---

## 1. System overview

DiraScan aggregates Israeli rental listings from Yad2, Madlan, and (optionally)
Facebook groups, stores them in PostGIS, and serves them to a React map UI.

```
┌────────────┐   /api/*    ┌──────────────┐   enqueue    ┌──────────────────┐
│  React SPA │ ──────────▶ │   FastAPI    │ ───────────▶ │  PostgreSQL +    │
│ (port 3000)│ ◀────────── │  (port 8000) │ ◀─────────── │  PostGIS         │
└────────────┘   listings  └──────────────┘   results    │  (port 5432)     │
                                                          │  = data + queue  │
                                                          └────────┬─────────┘
                                                       claim jobs  │  ▲ results
                                                                   ▼  │
                                                          ┌──────────────────┐
                                                          │  scraper worker  │
                                                          │ `dirascan worker`│
                                                          │ Playwright/Chrome│
                                                          └──────────────────┘
```

Four runtime services (plus a one-shot migrator), wired in `docker-compose.yml`:

| Service    | Role |
|------------|------|
| `db`       | PostgreSQL 16 + PostGIS. Stores listings **and** is the scrape job queue. |
| `migrate`  | One-shot: runs Alembic to head, then exits. `api`/`scraper` wait on it. |
| `api`      | FastAPI. Serves listings/geo data and **enqueues** scrape jobs. Imports no crawlers. |
| `scraper`  | Persistent worker (`dirascan worker`). Runs the crawlers (Chromium lives here). |
| `frontend` | Vite dev server hosting the React SPA. |

Boot order is enforced with healthchecks and `depends_on`:
`db` (healthy) → `migrate` (completed) → `api` + `scraper`.

---

## 2. The core invariant: the API never imports Playwright

The original production bug was that the API imported the scrape router, which
imported all crawlers — and the Yad2/Madlan crawlers import **Playwright**, which
the API image does not install. The router failed to import and every scrape
trigger returned a generic error.

The rule that prevents this:

> **Nothing under `api/` may import a crawler, `dirascan.runner`, or Playwright.**

`POST /scrape/trigger` imports only `SearchFilters` (a plain dataclass),
`create_scrape_run`, and the ORM models. This is enforced by a test —
`api/tests/test_import_isolation.py` imports the FastAPI app in a fresh
interpreter and asserts that `playwright`, `dirascan.crawlers.*`, and
`dirascan.runner` are absent from `sys.modules`. It runs in CI.

---

## 3. Scrape lifecycle (queue + worker)

Scraping is a queue, not a background task. Postgres is the queue; the
`scrape_runs` table is both the work queue and the audit log.

```
UI "scrape" button
   │  POST /scrape/trigger { sources:[...], filters:{city, price, rooms, ...} }
   ▼
API: create_scrape_run(...)              → INSERT scrape_runs (status='queued')
   │  202 { run_id, status:'queued' }
   ▼
Worker loop (dirascan worker):
   claim_next_job()                       → UPDATE ... SET status='running',
   │                                          started_at=NOW()
   │   WHERE id = (SELECT id ... WHERE status='queued'
   │               ORDER BY triggered_at  FOR UPDATE SKIP LOCKED LIMIT 1)
   ▼
run_scrape_job(run_id, sources, filters):
   for each source:                       → crawler.scrape(filters)  (Playwright)
       upsert_listing(...) per result     → INSERT/UPDATE listings (+ listing_sources)
       db.commit()  (per source; one bad source rolls back & is skipped, not fatal)
   complete_scrape_run(...)               → status='completed' | 'failed',
                                              listings_found / listings_new counts
   ▼
UI polls GET /scrape/runs/{id} every 3s until completed/failed,
then refetches /listings → new pins appear on the map.
```

Key properties:

- **Atomic claim.** `claim_next_job` uses `FOR UPDATE SKIP LOCKED`, so multiple
  workers never grab the same row.
- **Stale recovery.** On startup the worker marks any run that has been
  `running` longer than `STALE_RUNNING_MINUTES` (30) as `failed`. Recovery
  measures **runtime** via `started_at` (stamped at claim) — not `triggered_at`
  (enqueue time) — so a job that merely waited a long time in the queue is never
  mistaken for a crashed one. Legacy rows without `started_at` fall back to
  `triggered_at` via `COALESCE`.
- **Per-source isolation.** A failure persisting one source rolls back that
  transaction so it can't poison the others; remaining sources still write and
  the run completes with the error recorded.
- **Filters round-trip.** The API stores filters as JSONB (`_filters_to_dict`,
  with the single `neighborhood` widened to `neighborhoods[]`); the worker
  rebuilds them with `filters_from_dict`. The round-trip is covered by tests.

The synchronous `dirascan scrape` CLI shares `runner.py` for one-off local runs
(bypassing the queue).

---

## 4. Browse / read path

```
React (useListings / useGeo)
   → api/client.ts (baseURL '/api')
   → Vite proxy strips '/api' → FastAPI
```

| Endpoint | Purpose |
|----------|---------|
| `GET /listings` | Paginated search: `city`, `neighborhood`, `price_*`, `rooms_*`, `sources[]`, spatial (`lat`/`lng`/`radius_m` **or** `polygon_geojson`), `sort_by`/`order`, `page`/`page_size`. |
| `GET /cities` | Canonical Hebrew city list (drives the city picker). |
| `GET /neighborhoods?city=` | Distinct neighborhoods seen in listings for a city (drives the dependent neighborhood picker). |
| `GET /scrape/runs/{id}` | Poll a scrape run. |
| `GET /health` | Liveness. |

Spatial filtering is **mutually exclusive**: `polygon_geojson` takes precedence
over `lat`/`lng`/`radius_m`. Note that a drawn polygon/radius filters listings on
**display** only — it is not forwarded to the source crawlers (Yad2/Madlan can't
do arbitrary polygon queries), which fetch by city.

---

## 5. Data model

```
listings            canonical listing rows; PostGIS POINT geometry (SRID 4326)
listing_sources     (source, source_id) — dedup; many sources → one listing
scrape_runs         the job queue + audit log
                    status: queued → running → completed | failed
                    triggered_at (enqueue) · started_at (claim) · completed_at
```

- **Deduplication** is on `(source, source_id)` via `upsert_listing`'s
  `ON CONFLICT`. The same flat listed on Yad2 *and* Madlan collapses to one
  canonical `listings` row with two `listing_sources` entries.
- **Geometry** is written as `POINT(lng lat)` (longitude first, PostGIS
  convention) with SRID 4326. `Listing.lat`/`lng` are Python `@property`
  accessors over the geometry — **not** real columns, so they can't be used in
  SQLAlchemy filter expressions; spatial queries use PostGIS functions.

### Migrations

Alembic, linear chain `001 → 007` (the `sqlalchemy.url` in `alembic.ini` is
intentionally blank; `env.py` sets it from `dirascan.settings`). Notable recent
ones: `005` adds the `queued` status + polling indexes, `006` neighborhood
indexes, `007` the `started_at` column for accurate stale recovery. They apply
automatically via the `migrate` service on `docker compose up`.

---

## 6. CI

`.github/workflows/ci.yml` runs three jobs on every push/PR:

- **scraper** — spins up a real `postgis/postgis` service, runs `dirascan
  migrate`, then the full suite, so the `FOR UPDATE SKIP LOCKED` queue-claim and
  stale-recovery tests (gated on `TEST_DATABASE_URL`) actually execute.
- **api** — installs `dirascan` (base, no browsers) + the API and runs the
  route/schema tests, including the import-isolation guard.
- **frontend** — `npm ci`, Vitest, and `tsc && vite build`.
