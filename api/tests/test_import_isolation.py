"""Architecture guard: importing the FastAPI app must NOT pull in Playwright or
any crawler/runner module.

This is the exact regression that broke scraping originally — the API container
imported the crawlers (which import Playwright, absent from the API image), so
the scrape router failed to load. Run the import in a fresh interpreter so the
check isn't masked by modules other tests already imported.
"""

from __future__ import annotations

import os
import subprocess
import sys


def test_api_app_import_excludes_playwright_and_crawlers():
    api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    scraper_dir = os.path.abspath(os.path.join(api_dir, "..", "scraper"))
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [scraper_dir, api_dir, env.get("PYTHONPATH", "")]
    )
    code = (
        "import main\n"  # FastAPI app factory — registers all routers
        "import sys\n"
        "bad = [m for m in sys.modules if m.startswith('playwright') "
        "or m.startswith('dirascan.crawlers') or m == 'dirascan.runner']\n"
        "assert not bad, bad\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=api_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "Importing the API pulled in worker-only modules:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
