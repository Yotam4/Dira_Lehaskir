"""
Anti-detection helpers for Playwright-based scrapers.

Provides: UA rotation, viewport randomisation, Chromium launch flags,
JS fingerprint patching, delay jitter, and human-like page interactions.
"""
from __future__ import annotations

import asyncio
import logging
import random

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# User-agent pool — real Chrome strings, top market-share builds (2024-Q1)
# ---------------------------------------------------------------------------

_USER_AGENTS: list[str] = [
    # Chrome 124 — Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome 123 — Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome 124 — macOS Ventura
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome 123 — macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome 124 — Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome 122 — Windows (still heavily used)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Edge 124 — Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# ---------------------------------------------------------------------------
# Viewport pool — common desktop resolutions
# ---------------------------------------------------------------------------

_VIEWPORTS: list[dict[str, int]] = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 800},
]


def random_user_agent() -> str:
    return random.choice(_USER_AGENTS)


def random_viewport() -> dict[str, int]:
    return random.choice(_VIEWPORTS)


# ---------------------------------------------------------------------------
# Chromium launch flags
# ---------------------------------------------------------------------------

def browser_launch_args() -> list[str]:
    """Flags that suppress the most-checked headless-browser signals."""
    return [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--disable-infobars",
        "--no-first-run",
        "--no-zygote",
        "--disable-gpu",
    ]


# ---------------------------------------------------------------------------
# JS init script — patches navigator/window tells
# ---------------------------------------------------------------------------

_INIT_SCRIPT = """
// 1. Remove navigator.webdriver — the single most-checked headless signal
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// 2. Fake a non-empty plugin list (headless returns 0 plugins by default)
Object.defineProperty(navigator, 'plugins', {
  get: () => {
    const arr = [
      {name: 'Chrome PDF Plugin',  filename: 'internal-pdf-viewer',   description: 'Portable Document Format'},
      {name: 'Chrome PDF Viewer',  filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
      {name: 'Native Client',      filename: 'internal-nacl-plugin',  description: ''},
    ];
    arr.__proto__ = PluginArray.prototype;
    return arr;
  }
});

// 3. Language matching the locale we pass to Playwright
Object.defineProperty(navigator, 'languages', {
  get: () => ['he-IL', 'he', 'en-US', 'en'],
});

// 4. window.chrome expected by many Israeli sites
window.chrome = {runtime: {}, loadTimes: () => {}, csi: () => {}, app: {}};

// 5. Permissions API — real browsers answer 'granted' for notifications
try {
  const origQuery = navigator.permissions.query.bind(navigator.permissions);
  navigator.permissions.query = (desc) =>
    desc && desc.name === 'notifications'
      ? Promise.resolve({state: Notification.permission, onchange: null})
      : origQuery(desc);
} catch (_) {}
"""


async def apply_stealth_init(context_or_page) -> None:  # type: ignore[no-untyped-def]
    """
    Install the stealth init script on a BrowserContext (preferred) or Page.
    When installed on a context, every new page in that context is patched
    automatically before any JS runs.
    """
    await context_or_page.add_init_script(_INIT_SCRIPT)


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------

async def jitter_sleep(base_seconds: float) -> None:
    """Sleep for base × U(0.6, 1.7) so inter-request timing is never uniform."""
    await asyncio.sleep(random.uniform(base_seconds * 0.6, base_seconds * 1.7))


# ---------------------------------------------------------------------------
# Human-like micro-interactions
# ---------------------------------------------------------------------------

async def human_scroll(page) -> None:  # type: ignore[no-untyped-def]
    """
    Scroll the page in a few randomised steps to mimic a user skimming content.
    Non-fatal — silently skips if the page is already closing.
    """
    try:
        steps = random.randint(2, 5)
        for _ in range(steps):
            await page.mouse.wheel(0, random.randint(150, 500))
            await asyncio.sleep(random.uniform(0.1, 0.4))
        # Pause as if reading
        await asyncio.sleep(random.uniform(0.4, 1.0))
    except Exception:
        pass
