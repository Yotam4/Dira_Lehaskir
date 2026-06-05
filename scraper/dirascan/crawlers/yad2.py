from __future__ import annotations

import asyncio
import logging
from typing import Any

from playwright.async_api import BrowserContext, async_playwright

from dirascan import stealth as _stealth
from dirascan.base.crawler import BaseCrawler, RawListing, SearchFilters
from dirascan.cities import CITY_TO_YAD2_CODE as CITY_CODES
from dirascan.settings import settings

logger = logging.getLogger(__name__)

_YAD2_FEED_FRAGMENT = "gw.yad2.co.il/feed-search-legato"
_YAD2_BASE_URL = "https://www.yad2.co.il/realestate/rent"


class Yad2Crawler(BaseCrawler):
    """
    Scraper for yad2.co.il — Israel's largest real-estate classifieds.

    Uses Playwright to navigate the SPA and intercepts the JSON feed API
    responses from gw.yad2.co.il rather than parsing the DOM directly.
    Paginates via the ``page`` query parameter.
    """

    source_name = "yad2"

    # ------------------------------------------------------------------
    # URL / query param helpers
    # ------------------------------------------------------------------

    def _city_code(self, city: str) -> str | None:
        if not city:
            return None
        return CITY_CODES.get(city.strip()) or CITY_CODES.get(city.strip().lower())

    def _build_url(self, filters: SearchFilters, page: int = 1) -> str:
        params: list[str] = []

        code = self._city_code(filters.city)
        if code:
            params.append(f"city={code}")

        if filters.rooms_min is not None or filters.rooms_max is not None:
            r_min = int(filters.rooms_min) if filters.rooms_min is not None else 1
            r_max = int(filters.rooms_max) if filters.rooms_max is not None else 20
            params.append(f"rooms={r_min}-{r_max}")

        if filters.price_min is not None or filters.price_max is not None:
            p_min = filters.price_min or 0
            p_max = filters.price_max or 99999
            params.append(f"price={p_min}-{p_max}")

        if page > 1:
            params.append(f"page={page}")

        qs = "&".join(params)
        return f"{_YAD2_BASE_URL}{'?' + qs if qs else ''}"

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_item(self, item: dict[str, Any], filters: SearchFilters) -> RawListing | None:
        if item.get("type") not in ("ad", "feed_item"):
            # Skip promoted banners, separators, etc.
            if not item.get("id"):
                return None

        item_id = str(item.get("id", ""))
        if not item_id:
            return None

        link_token = item.get("link_token") or item_id
        url = f"https://www.yad2.co.il/item/{link_token}"

        # Price
        price_raw = item.get("price")
        price: int | None = None
        if isinstance(price_raw, (int, float)):
            price = int(price_raw)
        elif isinstance(price_raw, str):
            digits = price_raw.replace(",", "").replace(".", "").strip()
            price = int(digits) if digits.isdigit() else None

        # Rooms
        rooms_raw = item.get("rooms")
        rooms: float | None = None
        try:
            rooms = float(rooms_raw) if rooms_raw is not None else None
        except (ValueError, TypeError):
            pass

        # Sqm
        sqm_raw = item.get("square_meters")
        sqm: float | None = None
        try:
            sqm = float(sqm_raw) if sqm_raw is not None else None
        except (ValueError, TypeError):
            pass

        # Floor
        floor_raw = item.get("floor")
        floor: int | None = None
        try:
            floor = int(floor_raw) if floor_raw is not None else None
        except (ValueError, TypeError):
            pass

        # Location
        coords = item.get("coordinates") or {}
        try:
            lat: float | None = float(coords["latitude"]) if coords.get("latitude") is not None else None
            lng: float | None = float(coords["longitude"]) if coords.get("longitude") is not None else None
        except (ValueError, TypeError):
            lat, lng = None, None

        # Address
        street = item.get("street") or ""
        house_num = item.get("house_number") or ""
        address = f"{street} {house_num}".strip() or None

        city = item.get("city_text") or filters.city or ""
        neighborhood = item.get("neighborhood_text") or None

        images = [
            img["src"]
            for img in (item.get("images") or [])
            if isinstance(img, dict) and img.get("src")
        ]

        title = (
            item.get("title")
            or f"דירה {int(rooms) if rooms else '?'} חדרים ב{city}"
        )

        return RawListing(
            source=self.source_name,
            source_id=item_id,
            original_url=url,
            title=title,
            description=item.get("description") or item.get("info_text"),
            price_raw=str(price_raw) if price_raw is not None else None,
            price=price,
            rooms_raw=str(rooms_raw) if rooms_raw is not None else None,
            rooms=rooms,
            sqm_raw=str(sqm_raw) if sqm_raw is not None else None,
            sqm=sqm,
            floor_raw=str(floor_raw) if floor_raw is not None else None,
            floor=floor,
            address=address,
            city=city,
            neighborhood=neighborhood,
            lat=lat,
            lng=lng,
            images=images,
            raw_data=item,
        )

    def _parse_response(
        self, data: dict[str, Any], filters: SearchFilters
    ) -> tuple[list[RawListing], int]:
        """Return (listings, total_pages) from a captured API JSON payload."""
        feed = (data.get("data") or {}).get("feed") or {}
        feed_items: list[dict] = feed.get("feed_items") or []
        total_pages = int(feed.get("total_pages") or 1)

        listings: list[RawListing] = []
        for item in feed_items:
            try:
                listing = self._parse_item(item, filters)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                logger.warning("Yad2: failed to parse item %s: %s", item.get("id"), exc)

        return listings, total_pages

    # ------------------------------------------------------------------
    # Page fetcher — one Playwright page per pagination step
    # ------------------------------------------------------------------

    async def _fetch_page(
        self,
        context: BrowserContext,
        filters: SearchFilters,
        page_num: int,
    ) -> tuple[list[RawListing], int]:
        captured: list[dict] = []

        async def on_response(response):  # type: ignore[no-untyped-def]
            if _YAD2_FEED_FRAGMENT in response.url:
                try:
                    captured.append(await response.json())
                except Exception:
                    pass

        page = await context.new_page()
        page.on("response", on_response)

        url = self._build_url(filters, page_num)
        logger.info("Yad2: fetching page %d → %s", page_num, url)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
            await _stealth.human_scroll(page)
        except Exception as exc:
            logger.warning("Yad2: timeout/error on page %d: %s", page_num, exc)
        finally:
            await page.close()

        listings: list[RawListing] = []
        total_pages = 1
        for data in captured:
            batch, tp = self._parse_response(data, filters)
            listings.extend(batch)
            total_pages = max(total_pages, tp)

        return listings, total_pages

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    async def scrape(self, filters: SearchFilters) -> list[RawListing]:
        all_listings: list[RawListing] = []

        user_data_dir = settings.cookies_dir / "yad2"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as pw:
            # Persistent context keeps cookies / localStorage between runs so
            # the site sees us as a returning user rather than a fresh bot.
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=settings.playwright_headless,
                user_agent=_stealth.random_user_agent(),
                viewport=_stealth.random_viewport(),
                locale="he-IL",
                timezone_id="Asia/Jerusalem",
                args=_stealth.browser_launch_args(),
            )
            # Patch JS fingerprint tells on every page opened in this context.
            await _stealth.apply_stealth_init(context)
            try:
                page_num = 1
                total_pages = 1

                while page_num <= total_pages:
                    if filters.max_results and len(all_listings) >= filters.max_results:
                        break

                    batch, total_pages = await self._fetch_page(context, filters, page_num)

                    if not batch and page_num == 1:
                        logger.warning("Yad2: no listings captured on first page")
                        break

                    all_listings.extend(batch)
                    page_num += 1

                    if page_num <= total_pages:
                        await _stealth.jitter_sleep(settings.scraper_request_delay_seconds)
            finally:
                await context.close()

        if filters.max_results:
            all_listings = all_listings[: filters.max_results]

        logger.info("Yad2: scraped %d listings total", len(all_listings))
        return all_listings
