# CLAUDE.md — DiraScan Developer Guide

This file is the authoritative reference for AI coding assistants (Claude Code, etc.) working on this repo.

---

## Project Overview

**DiraScan** is a real-estate rental aggregator for the Israeli market. It scrapes listings from Yad2, Madlan, and Facebook groups, stores them in a PostGIS database, and displays them on an interactive Mapbox map.

**Stack:**
- Backend API: FastAPI (Python 3.11), SQLAlchemy 2, PostGIS/PostgreSQL 16
- Scraper: Playwright + facebook-scraper, packaged as `dirascan` (installed in Docker, volume-mounted for dev)
- Frontend: React 18, TypeScript, Vite, react-map-gl v7, @mapbox/mapbox-gl-draw, TanStack Query
- Infra: Docker Compose

---

## Repository Layout

```
Dira_Lehaskir/
├── api/                  FastAPI application
│   ├── main.py           App factory + route registration
│   ├── api/
│   │   ├── routers/
│   │   │   ├── listings.py   GET /listings, GET /listings/{id}
│   │   │   └── scrape.py     POST /scrape/trigger, GET /scrape/runs/{id}
│   │   ├── schemas/
│   │   │   ├── listing.py    ListingResponse, ListingsPage
│   │   │   └── scrape.py     ScrapeRequest, ScrapeRunResponse, ScrapeRunDetailResponse
│   │   └── deps.py           get_db dependency
│   ├── settings.py       Pydantic settings (reads from env)
│   └── tests/
│       ├── conftest.py   Fixtures + path patching for dirascan package
│       ├── test_listings.py
│       └── test_scrape.py
│
├── scraper/              dirascan Python package
│   ├── dirascan/
│   │   ├── base/crawler.py   RawListing dataclass, SearchFilters, ABCs
│   │   ├── crawlers/
│   │   │   ├── yad2.py       Playwright scraper (intercepts XHR)
│   │   │   ├── madlan.py     Playwright scraper (GraphQL)
│   │   │   └── facebook.py   facebook-scraper library wrapper
│   │   ├── nlp/hebrew.py     Regex extractors: price, rooms, sqm, floor
│   │   ├── db/
│   │   │   ├── models.py     SQLAlchemy ORM: Listing, ListingSource, ScrapeRun
│   │   │   ├── crud.py       create_scrape_run, complete_scrape_run, upsert_listing
│   │   │   └── session.py    SessionLocal factory
│   │   └── cli.py            `dirascan scrape` + `dirascan migrate` commands
│   ├── migrations/       Alembic migrations
│   └── tests/
│       └── test_nlp.py   Pure unit tests for Hebrew extractors
│
├── frontend/             React + TypeScript SPA
│   ├── src/
│   │   ├── pages/Home.tsx          Main layout
│   │   ├── components/
│   │   │   ├── FilterPanel.tsx     Hebrew filter UI
│   │   │   ├── ListingCard.tsx     Sidebar card
│   │   │   ├── ListingDetail.tsx   Expanded detail panel
│   │   │   ├── MapView.tsx         Mapbox map + draw tool
│   │   │   └── ScrapeButton.tsx    Trigger + poll scrape status
│   │   ├── hooks/useListings.ts    TanStack Query hook
│   │   ├── api/client.ts           Axios API client
│   │   ├── types/listing.ts        TypeScript interfaces
│   │   └── test/
│   │       ├── setup.ts            jest-dom setup
│   │       └── fixtures.ts         Shared mock data
│   └── src/components/*.test.tsx   Vitest component tests
│
├── docker-compose.yml
├── .env.example
└── CLAUDE.md             (this file)
```

---

## Key Architecture Decisions

### dirascan package path
`api/main.py` does `sys.path.insert(0, "/scraper")` so Docker can find the `dirascan` package. In tests, `api/tests/conftest.py` patches the path to the local `../scraper` directory before imports. Never change this pattern without updating both.

### Scraping is a queue + worker, NOT a background task
The API must never run crawlers in-process: the crawlers import Playwright, which
the API image doesn't install (doing so previously crashed the scrape router on
import). Instead:
- `POST /scrape/trigger` only **enqueues** a `ScrapeRun` row with `status='queued'`
  (via `create_scrape_run`) and returns. It imports no crawlers and no Playwright.
- The `scraper` service runs `dirascan worker` (`scraper/dirascan/worker.py`),
  which claims queued rows atomically (`FOR UPDATE SKIP LOCKED`), runs the crawlers
  through `dirascan/runner.py`, and records results. Postgres is the queue.
- The frontend polls `GET /scrape/runs/{id}` until `completed`/`failed`.

So: **never add crawler/Playwright imports to anything under `api/`**, and never
run a scrape from a FastAPI `BackgroundTask`. `api/tests/test_import_isolation.py`
guards this — it fails if importing the app pulls in `playwright`/`dirascan.crawlers`/
`dirascan.runner`. The synchronous `dirascan scrape` CLI shares `runner.py` for
one-off local runs.

### MapboxDraw instance
`MapView.tsx` uses a `useRef` to capture the `MapboxDraw` instance at creation time. Event handlers then use `drawRef.current.getAll()`. Never try to access the draw instance via `map._drawControl` — that property does not exist.

### Deduplication
`upsert_listing` in `crud.py` deduplicates on `(source, source_id)` via the `listing_sources` table. A single canonical `listings` row can have multiple source entries (e.g., same apartment on both Yad2 and Madlan).

### Spatial queries
Listings have a PostGIS `POINT` geometry (`SRID 4326`). The listings endpoint supports two mutually exclusive spatial modes — polygon takes precedence over point+radius.

---

## Running Tests

### Backend — NLP (no DB required)
```bash
cd scraper
pip install -e ".[dev]"
pytest tests/test_nlp.py -v
```

### Backend — API (no DB required, DB is fully mocked)
```bash
cd api
pip install -e ".[dev]"
# Make dirascan importable
PYTHONPATH=../scraper pytest tests/ -v
```

### Frontend
```bash
cd frontend
npm install
npm test          # single run
npm run test:watch  # watch mode
```

---

## Running the Full Stack

```bash
cp .env.example .env
# Fill in VITE_MAPBOX_TOKEN and FACEBOOK_EMAIL/FACEBOOK_PASSWORD

# Brings up db, runs migrations (the one-shot `migrate` service), then starts
# the api, the scraper worker, and the frontend. Migrations run automatically —
# api and scraper wait for `migrate` to finish before starting.
docker compose up -d

# Scraping is automatic: the `scraper` service runs `dirascan worker`, polling
# the queue for jobs enqueued by POST /scrape/trigger (the UI's "scrape" button).

# Optional: run a one-off synchronous scrape (bypasses the queue/worker)
docker compose run --rm scraper dirascan scrape --city "תל אביב" --source yad2
```

### Ports
| Service  | Port |
|----------|------|
| Frontend | 3000 |
| API      | 8000 |
| DB       | 5432 |

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/listings` | Paginated listing search with filters |
| `GET` | `/listings/{id}` | Single listing detail |
| `POST` | `/scrape/trigger` | Trigger background scrape |
| `GET` | `/scrape/runs/{id}` | Poll scrape run status |
| `GET` | `/health` | Health check |

### Key filter params for `GET /listings`
- `city`, `neighborhood` — case-insensitive text match
- `lat`, `lng`, `radius_m` — point + radius (metres)
- `polygon_geojson` — GeoJSON Polygon geometry string (takes precedence over point)
- `price_min`, `price_max`, `rooms_min`, `rooms_max`
- `source` — `yad2` | `madlan` | `facebook`
- `page`, `page_size` (max 100)

---

## Conventions

- Python: type hints on all function signatures, `from __future__ import annotations` at top
- SQLAlchemy: use `db.flush()` (not `db.commit()`) inside CRUD helpers — the caller controls the transaction
- React: inline styles (no CSS modules or Tailwind); RTL Hebrew text is handled by the browser automatically since the data is Hebrew
- All money is in ILS (Israeli New Shekel); sqm is in square metres
- `rooms` is `float` (3.5 rooms is very common in Israel)

---

## Common Pitfalls

1. **PostGIS geometry serialization** — `Listing.lat` and `Listing.lng` are `@property` fields that call `to_shape()`. They are not real DB columns and cannot be used in SQLAlchemy filter expressions.

2. **facebook-scraper rate limiting** — Authenticated scraping requires `FACEBOOK_EMAIL` + `FACEBOOK_PASSWORD`. Without credentials, only public posts are returned. The scraper has a built-in delay (`SCRAPER_REQUEST_DELAY_SECONDS`).

3. **Mapbox token** — `VITE_MAPBOX_TOKEN` must start with `pk.` (public token). Secret tokens (`sk.`) will fail CORS on the browser.

4. **Alembic** — Run migrations from inside the `scraper/` directory or container where `alembic.ini` lives. The DB URL is set programmatically from `dirascan.settings` — the `sqlalchemy.url` line in `alembic.ini` is intentionally empty.
