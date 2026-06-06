# DiraScan — Israeli Rental Aggregator

DiraScan scrapes rental listings from **Yad2**, **Madlan**, and **Facebook groups**, stores them in a PostGIS database, and displays them on an interactive Mapbox map with polygon drawing, price/room filters, and live scrape triggering.

---

## Prerequisites

| Tool | Min version |
|------|-------------|
| Docker + Docker Compose | v2.20 |
| Node.js (for local frontend dev) | v20 |
| Python (for local backend dev) | 3.11 |
| Mapbox public token | `pk.*` |

---

## Quick Start

```bash
git clone https://github.com/yotam4/dira_lehaskir.git
cd dira_lehaskir

# 1. Configure secrets
cp .env.example .env
#    Edit .env — fill in VITE_MAPBOX_TOKEN at minimum

# 2. Start the whole stack. The one-shot `migrate` service applies all
#    migrations first; then the api, the scraper worker, and the frontend start.
docker compose up -d

# 3. Open the app
open http://localhost:3000
```

> Migrations run **automatically** — `api` and `scraper` wait for the `migrate`
> service to finish before starting. Scraping runs in a persistent **worker**
> (`dirascan worker`) that polls a Postgres-backed queue, so the "scrape" button
> in the UI works out of the box.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_DB` | Yes | Database name (default: `dirascan`) |
| `POSTGRES_USER` | Yes | DB user |
| `POSTGRES_PASSWORD` | Yes | DB password |
| `DATABASE_URL` | Yes | Full connection string |
| `API_SECRET_KEY` | Yes | Random secret for the API |
| `CORS_ORIGINS` | Yes | Frontend origin (e.g. `http://localhost:3000`) |
| `VITE_MAPBOX_TOKEN` | Yes | Mapbox **public** token (`pk.*`). Without it the app still loads, but the map area shows a token error. |
| `VITE_API_BASE_URL` | No | Vite dev-proxy target. Set to `http://api:8000` in Docker; defaults to `http://localhost:8000` for local dev. |
| `FACEBOOK_EMAIL` | No | Facebook account for authenticated scraping (Facebook source is an optional extra — see below). |
| `FACEBOOK_PASSWORD` | No | Facebook account password |
| `PLAYWRIGHT_HEADLESS` | No | `true` (default) or `false` |
| `SCRAPER_REQUEST_DELAY_SECONDS` | No | Delay between scraper requests (default: `2.0`) |
| `TEST_DATABASE_URL` | No | Set to run the Postgres-gated worker queue tests (used by CI). |

---

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | React map UI |
| API | http://localhost:8000 | FastAPI backend (enqueues scrapes; serves listings) |
| API docs | http://localhost:8000/docs | Interactive Swagger UI |
| Scraper worker | — (background) | `dirascan worker` — claims queued jobs and runs the crawlers (Playwright/Chromium) |
| DB | localhost:5432 | PostgreSQL + PostGIS (also the scrape job queue) |

---

## Running a Scrape

### Via the UI (recommended)
Click the **"סרוק עכשיו"** (Scan Now) button, pick a city and sources, and submit.
This enqueues a job; the worker picks it up and runs the crawlers. The button polls
status every 3 seconds and shows a completion count when finished — new listings
then appear on the map automatically.

### Via CLI (one-off, synchronous — bypasses the queue/worker)
```bash
# Scrape Yad2 listings in Tel Aviv
docker compose run --rm scraper dirascan scrape --city "תל אביב" --source yad2

# Scrape all installed sources
docker compose run --rm scraper dirascan scrape --city "תל אביב"

# Specify price range
docker compose run --rm scraper dirascan scrape --city "תל אביב" --price-min 3000 --price-max 7000
```

> **Facebook is optional.** `facebook-scraper` is an optional extra and is **not**
> installed in the default image, so only Yad2 and Madlan run out of the box. To
> enable it, install the extra (`pip install -e ".[facebook]"` in the scraper
> image) and set `FACEBOOK_EMAIL`/`FACEBOOK_PASSWORD`.

---

## Development

### Backend API

```bash
cd api
pip install -e ".[dev]"
# Run with auto-reload (requires DB to be running)
PYTHONPATH=../scraper uvicorn main:app --reload --port 8000

# Tests (no DB required — fully mocked)
PYTHONPATH=../scraper pytest tests/ -v
```

### Scraper

```bash
cd scraper
pip install -e ".[dev]"
playwright install chromium

# NLP unit tests (no DB, no network)
pytest tests/test_nlp.py -v
```

### Frontend

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000 with HMR

npm test          # run all component tests
npm run test:watch  # watch mode
```

---

## Architecture

Scraping is a **queue + worker**, never an in-process background task — the API
image doesn't ship Playwright, so the API must not import the crawlers.

```
Browser → React SPA (port 3000)
            │  /api/* (Vite proxy in dev; service DNS in Docker)
            ▼
        FastAPI (port 8000)              ── imports NO crawlers / NO Playwright
            ├── GET  /listings           ← Postgres query with spatial filters
            ├── GET  /cities             ← canonical city list
            ├── GET  /neighborhoods?city ← distinct neighborhoods for a city
            ├── POST /scrape/trigger     ← ENQUEUES a ScrapeRun (status='queued')
            └── GET  /scrape/runs/{id}   ← poll status (queued/running/completed/failed)
                        │
                        ▼
              PostgreSQL + PostGIS  ← also the job queue
              ├── listings          (canonical rows; PostGIS POINT geometry)
              ├── listing_sources   (dedup: source × source_id)
              └── scrape_runs       (the queue + audit log)
                        ▲
                        │ claims jobs (FOR UPDATE SKIP LOCKED), records results
                        │
              dirascan worker  (`dirascan worker`, separate container)
              └── runner.py → crawlers (Playwright/Chromium live HERE)
                  ├── Yad2Crawler     (intercepts the XHR feed)
                  ├── MadlanCrawler   (GraphQL)
                  └── FacebookCrawler  (optional extra; off by default)
```

The frontend triggers a scrape, then polls the run until `completed`/`failed`;
on completion it refetches `/listings` so new results appear on the map.

### Deduplication
Each crawler returns a `source_id` (e.g., the Yad2 item token). On upsert, the `listing_sources` table is checked for `(source, source_id)`. If found, the existing listing is updated; if not, a new one is created. This prevents duplicates even when the same apartment is re-scraped, and a single canonical listing can have multiple sources (e.g. the same flat on Yad2 *and* Madlan).

For the full design — request lifecycle, the queue/worker contract, the data model, and the "API never imports Playwright" rule — see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Database Migrations

Migrations are managed with Alembic inside the `scraper/` directory and run
**automatically** on `docker compose up` via the one-shot `migrate` service — you
don't normally run them by hand.

```bash
# Apply all pending migrations manually (rarely needed)
docker compose run --rm scraper dirascan migrate

# Or directly with Alembic (from inside scraper/, where alembic.ini lives)
cd scraper
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "add_column_x"
```

---

## Project Structure

```
├── api/                  FastAPI app (enqueues scrapes; serves listings — no crawlers)
├── scraper/              dirascan package: crawlers, worker, runner, Alembic migrations
├── frontend/             React + TypeScript SPA
├── docs/
│   └── ARCHITECTURE.md   System design, request lifecycle, queue/worker contract
├── .github/workflows/    CI (scraper + PostGIS, api, frontend)
├── docker-compose.yml
├── .env.example
├── CLAUDE.md             AI coding assistant guide
└── README.md             (this file)
```

---

## Testing & CI

Every push runs three jobs (`.github/workflows/ci.yml`): the scraper suite against
a real **PostGIS** service (so the worker queue-claim tests actually run), the API
suite, and the frontend (Vitest + `tsc && vite build`).

```bash
# Scraper (NLP + crawlers + worker). Add TEST_DATABASE_URL to run the queue tests.
cd scraper && pip install -e ".[dev]" && PYTHONPATH=. pytest tests/ -v

# API (DB fully mocked)
cd api && pip install -e ".[dev]" && PYTHONPATH=../scraper pytest tests/ -v

# Frontend
cd frontend && npm ci && npm test && npm run build
```
