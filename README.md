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

# 2. Start all services
docker compose up -d db api frontend

# 3. Run database migrations (first time only)
docker compose run --rm scraper dirascan migrate

# 4. Open the app
open http://localhost:3000
```

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
| `VITE_MAPBOX_TOKEN` | Yes | Mapbox **public** token (`pk.*`) |
| `FACEBOOK_EMAIL` | No | Facebook account for authenticated scraping |
| `FACEBOOK_PASSWORD` | No | Facebook account password |
| `PLAYWRIGHT_HEADLESS` | No | `true` (default) or `false` |
| `SCRAPER_REQUEST_DELAY_SECONDS` | No | Delay between scraper requests (default: `2.0`) |

---

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | React map UI |
| API | http://localhost:8000 | FastAPI backend |
| API docs | http://localhost:8000/docs | Interactive Swagger UI |
| DB | localhost:5432 | PostgreSQL + PostGIS |

---

## Running a Scrape

### Via the UI
Click the **"סרוק עכשיו"** (Scan Now) button in the top-left of the UI. The button polls status every 3 seconds and shows a completion count when finished.

### Via CLI
```bash
# Scrape Yad2 listings in Tel Aviv
docker compose run --rm --profile scraper scraper \
  dirascan scrape --city "תל אביב" --source yad2

# Scrape all sources
docker compose run --rm --profile scraper scraper \
  dirascan scrape --city "תל אביב"

# Specify price range
docker compose run --rm --profile scraper scraper \
  dirascan scrape --city "תל אביב" --price-min 3000 --price-max 7000
```

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

```
Browser → React SPA (port 3000)
            │
            │ /api/* (proxied in dev, direct in prod)
            ▼
        FastAPI (port 8000)
            │
            ├── GET /listings          ← Postgres query with spatial filters
            ├── POST /scrape/trigger   ← Starts background scrape task
            └── GET /scrape/runs/{id}  ← Poll scrape status
                        │
                        ▼
                  dirascan package
                  ├── Yad2Crawler   (Playwright, intercepts XHR feed)
                  ├── MadlanCrawler (Playwright, GraphQL)
                  └── FacebookCrawler (facebook-scraper library)
                        │
                        ▼
                  PostgreSQL + PostGIS
                  ├── listings         (canonical listing rows)
                  ├── listing_sources  (deduplication: source × source_id)
                  └── scrape_runs      (audit log)
```

### Deduplication
Each crawler returns a `source_id` (e.g., the Yad2 item token). On upsert, the `listing_sources` table is checked for `(source, source_id)`. If found, the existing listing is updated; if not, a new one is created. This prevents duplicates even when the same apartment is re-scraped.

---

## Database Migrations

Migrations are managed with Alembic inside the `scraper/` directory:

```bash
# Apply all pending migrations
docker compose run --rm scraper dirascan migrate

# Or manually with Alembic
cd scraper
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "add_column_x"
```

---

## Project Structure

```
├── api/                  FastAPI app
├── scraper/              dirascan Python package + Alembic migrations
├── frontend/             React + TypeScript SPA
├── docker-compose.yml
├── .env.example
├── CLAUDE.md             AI coding assistant guide
└── README.md             (this file)
```
