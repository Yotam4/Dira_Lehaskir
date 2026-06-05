"""Tests for the scrape worker / runner.

The orchestration tests (filters round-trip, run_scrape_job) run fully offline
with a fake crawler. The queue-claim tests use raw Postgres SQL (FOR UPDATE SKIP
LOCKED), so they require a real Postgres and are skipped unless TEST_DATABASE_URL
is set.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from dirascan.base.crawler import BaseCrawler, RawListing, SearchFilters
from dirascan.db.crud import _filters_to_dict, filters_from_dict
from dirascan import runner


class EchoCrawler(BaseCrawler):
    """A network-free crawler that returns one canned listing."""

    source_name = "echo"

    async def scrape(self, filters: SearchFilters) -> list[RawListing]:
        return [
            RawListing(
                source="echo",
                source_id="echo-1",
                title="echo",
                city=filters.city or "test",
                price=5000,
            )
        ]


class BoomCrawler(BaseCrawler):
    """Returns one listing whose persistence will be made to fail in a test."""

    source_name = "boom"

    async def scrape(self, filters: SearchFilters) -> list[RawListing]:
        return [RawListing(source="boom", source_id="boom-1", title="boom", city="x", price=1)]


# ---------------------------------------------------------------------------
# filters round-trip
# ---------------------------------------------------------------------------

class TestFiltersRoundTrip:
    def test_round_trip_preserves_fields(self):
        original = SearchFilters(
            city="תל אביב",
            neighborhoods=["פלורנטין"],
            lat=32.06,
            lng=34.77,
            radius_m=1500,
            polygon_geojson='{"type":"Polygon","coordinates":[]}',
            price_min=3000,
            price_max=8000,
            rooms_min=2.0,
            rooms_max=4.0,
            max_results=25,
        )
        restored = filters_from_dict(_filters_to_dict(original))
        assert restored == original

    def test_empty_dict_yields_defaults(self):
        f = filters_from_dict({})
        assert f.city == ""
        assert f.neighborhoods == []
        assert f.price_min is None


# ---------------------------------------------------------------------------
# run_scrape_job orchestration (mocked DB + fake crawler)
# ---------------------------------------------------------------------------

class TestRunScrapeJob:
    async def test_success_completes_with_counts(self, monkeypatch):
        run_id = uuid.uuid4()
        mock_run = MagicMock(status="running")
        db = MagicMock()
        db.get.return_value = mock_run

        monkeypatch.setitem(runner.CRAWLERS, "echo", EchoCrawler)
        monkeypatch.setattr(runner, "upsert_listing", lambda _db, _raw: (MagicMock(), True))
        complete = MagicMock()
        monkeypatch.setattr(runner, "complete_scrape_run", complete)

        await runner.run_scrape_job(run_id, ["echo"], SearchFilters(city="תל אביב"), db)

        complete.assert_called_once()
        kwargs = complete.call_args.kwargs
        assert kwargs["listings_found"] == 1
        assert kwargs["listings_new"] == 1
        assert kwargs["error_message"] is None

    async def test_unavailable_source_recorded_as_error(self, monkeypatch):
        run_id = uuid.uuid4()
        db = MagicMock()
        db.get.return_value = MagicMock(status="running")
        complete = MagicMock()
        monkeypatch.setattr(runner, "complete_scrape_run", complete)

        await runner.run_scrape_job(run_id, ["does-not-exist"], SearchFilters(), db)

        kwargs = complete.call_args.kwargs
        assert "does-not-exist" in (kwargs["error_message"] or "")
        assert kwargs["listings_found"] == 0

    async def test_failing_source_rolls_back_and_next_source_still_persists(self, monkeypatch):
        """A persistence failure in one source must roll back (so the session
        isn't poisoned) and must not prevent later sources from being saved."""
        run_id = uuid.uuid4()
        db = MagicMock()
        db.get.return_value = MagicMock(status="running")

        monkeypatch.setitem(runner.CRAWLERS, "boom", BoomCrawler)
        monkeypatch.setitem(runner.CRAWLERS, "echo", EchoCrawler)

        def fake_upsert(_db, raw):
            if raw.source == "boom":
                raise ValueError("bad listing")  # simulate a flush/constraint failure
            return (MagicMock(), True)

        monkeypatch.setattr(runner, "upsert_listing", fake_upsert)
        complete = MagicMock()
        monkeypatch.setattr(runner, "complete_scrape_run", complete)

        await runner.run_scrape_job(run_id, ["boom", "echo"], SearchFilters(), db)

        db.rollback.assert_called_once()  # rolled back the poisoned 'boom' tx
        kwargs = complete.call_args.kwargs
        assert kwargs["listings_found"] == 1  # echo still persisted
        assert kwargs["listings_new"] == 1
        assert "boom" in (kwargs["error_message"] or "")


# ---------------------------------------------------------------------------
# Queue claim / recovery — requires real Postgres
# ---------------------------------------------------------------------------

_TEST_DB = os.getenv("TEST_DATABASE_URL")

pg = pytest.mark.skipif(not _TEST_DB, reason="set TEST_DATABASE_URL to run Postgres queue tests")


@pg
class TestQueueClaim:
    @pytest.fixture
    def session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(_TEST_DB)
        Session = sessionmaker(bind=engine)
        s = Session()
        yield s
        s.rollback()
        s.close()

    def _enqueue(self, session, **kw):
        from dirascan.db.models import ScrapeRun

        run = ScrapeRun(id=uuid.uuid4(), sources=["yad2"], filters={}, status="queued", **kw)
        session.add(run)
        session.commit()
        return run

    def test_claim_picks_oldest_queued_and_flips_running(self, session):
        from dirascan.worker import claim_next_job

        older = self._enqueue(session, triggered_at=datetime.now(timezone.utc) - timedelta(minutes=2))
        self._enqueue(session)

        claimed = claim_next_job(session)
        assert claimed is not None
        assert claimed.id == older.id
        assert claimed.status == "running"

    def test_claim_returns_none_when_empty(self, session):
        from dirascan.worker import claim_next_job
        from dirascan.db.models import ScrapeRun

        session.query(ScrapeRun).filter_by(status="queued").delete()
        session.commit()
        assert claim_next_job(session) is None

    def test_recover_stale_running(self, session):
        from dirascan.worker import _recover_stale_runs
        from dirascan.db.models import ScrapeRun

        stale = self._enqueue(session)
        stale.status = "running"
        stale.triggered_at = datetime.now(timezone.utc) - timedelta(hours=2)
        session.commit()

        _recover_stale_runs(session)
        session.refresh(stale)
        assert stale.status == "failed"
        assert "stale" in (stale.error_message or "").lower()

    def test_claim_stamps_started_at(self, session):
        from dirascan.worker import claim_next_job
        from dirascan.db.models import ScrapeRun

        session.query(ScrapeRun).filter_by(status="queued").delete()
        session.commit()
        self._enqueue(session)

        claimed = claim_next_job(session)
        assert claimed is not None
        assert claimed.started_at is not None

    def test_recovery_uses_start_time_not_enqueue_time(self, session):
        """A job that waited a long time in the queue then was just claimed must
        NOT be recovered as stale — recovery measures runtime, not queue wait."""
        from dirascan.worker import _recover_stale_runs
        from dirascan.db.models import ScrapeRun

        run = self._enqueue(session)
        # Enqueued 2h ago, but claimed just now (started_at = now).
        run.triggered_at = datetime.now(timezone.utc) - timedelta(hours=2)
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        session.commit()

        _recover_stale_runs(session)
        session.refresh(run)
        assert run.status == "running"  # still healthy, not failed
