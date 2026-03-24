import sys

# Make the dirascan scraper package importable (volume-mounted at /scraper)
sys.path.insert(0, "/scraper")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import listings, scrape
from settings import settings

app = FastAPI(title="DiraScan API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listings.router, prefix="/listings", tags=["listings"])
app.include_router(scrape.router, prefix="/scrape", tags=["scrape"])


@app.get("/health")
def health():
    return {"status": "ok"}
