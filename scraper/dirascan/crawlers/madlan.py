from __future__ import annotations

import asyncio
import logging
from typing import Any

from playwright.async_api import BrowserContext, async_playwright

from dirascan.base.crawler import BaseCrawler, RawListing, SearchFilters
from dirascan.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# City name -> Madlan URL slug  (Hebrew text used directly in the path)
# ---------------------------------------------------------------------------

CITY_SLUGS: dict[str, str] = {
    "תל אביב": "תל-אביב-יפו",
    "תל אביב יפו": "תל-אביב-יפו",
    "ירושלים": "ירושלים",
    "חיפה": "חיפה",
    "ראשון לציון": "ראשון-לציון",
    "פתח תקווה": "פתח-תקווה",
    "אשדוד": "אשדוד",
    "נתניה": "נתניה",
    "באר שבע": "באר-שבע",
    "בני ברק": "בני-ברק",
    "חולון": "חולון",
    "רמת גן": "רמת-גן",
    "גבעתיים": "גבעתיים",
    "הרצליה": "הרצליה",
    "כפר סבא": "כפר-סבא",
    "רחובות": "רחובות",
    "אשקלון": "אשקלון",
    "בת ים": "בת-ים",
    "מודיעין": "מודיעין-מכבים-רעות",
    "לוד": "לוד",
    "רמלה": "רמלה",
    "נס ציונה": "נס-ציונה",
    "רעננה": "רעננה",
    "הוד השרון": "הוד-השרון",
    "רמת השרון": "רמת-השרון",
    # English fallbacks
    "tel aviv": "תל-אביב-יפו",
    "jerusalem": "ירושלים",
    "haifa": "חיפה",
    "beer sheva": "באר-שבע",
    "netanya": "נתניה",
    "rishon lezion": "ראשון-לציון",
    "petah tikva": "פתח-תקווה",
    "ramat gan": "רמת-גן",
    "herzliya": "הרצליה",
}

_MADLAN_API_FRAGMENT = "madlan.co.il/api"
_MADLAN_BASE_URL = "https://www.madlan.co.il/for-rent"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class MadlanCrawler(BaseCrawler):
    """
    Scraper for madlan.co.il — map-centric real-estate portal.

    Uses Playwright to load the search SPA and intercepts GraphQL API
    responses from madlan.co.il/api. Supports city slug, price, and
    room filters encoded into the page URL and intercepted JSON payloads.
    """

    source_name = "madlan"

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def _city_slug(self, city: str) -> str:
        if not city:
            return ""
        return (
            CITY_SLUGS.get(city.strip())
            or CITY_SLUGS.get(city.strip().lower())
            or city.strip().replace(" ", "-")
        )

    def _build_url(self, filters: SearchFilters, page: int = 1) -> str:
        slug = self._city_slug(filters.city)
        base = f"{_MADLAN_BASE_URL}/{slug}" if slug else _MADLAN_BASE_URL

        params: list[str] = []

        if filters.price_min is not None:
            params.append(f"minPrice={filters.price_min}")
        if filters.price_max is not None:
            params.append(f"maxPrice={filters.price_max}")
        if filters.rooms_min is not None:
            params.append(f"minRooms={filters.rooms_min}")
        if filters.rooms_max is not None:
            params.append(f"maxRooms={filters.rooms_max}")
        if page > 1:
            params.append(f"page={page}")

        qs = "&".join(params)
        return f"{base}{'?' + qs if qs else ''}"

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def _parse_listing(self, item: dict[str, Any], filters: SearchFilters) -> RawListing | None:
        """Parse a single Madlan listing dict into a RawListing."""
        item_id = str(item.get("id") or item.get("listingId") or "")
        if not item_id:
            return None

        # URL — Madlan uses /item/<token> or /listing/<id>
        token = item.get("token") or item_id
        url = f"https://www.madlan.co.il/item/{token}"

        # Price — may be nested {"value": 5500, "currency": "ILS"} or a plain int
        price_field = item.get("price")
        price_raw: Any = None
        price: int | None = None
        if isinstance(price_field, dict):
            price_raw = price_field.get("value")
        else:
            price_raw = price_field
        price = self._safe_int(price_raw)

        # Rooms
        rooms_raw = item.get("rooms")
        rooms = self._safe_float(rooms_raw)

        # Size / sqm — field name varies across API versions
        sqm_raw = item.get("size") or item.get("squareMeters") or item.get("sqm")
        sqm = self._safe_float(sqm_raw)

        # Floor
        floor_raw = item.get("floor")
        floor = self._safe_int(floor_raw)

        # Address — nested or flat
        addr_field = item.get("address") or {}
        if isinstance(addr_field, dict):
            street = addr_field.get("street") or addr_field.get("streetName") or ""
            house_num = (
                addr_field.get("houseNumber")
                or addr_field.get("streetNumber")
                or ""
            )
            city = (
                addr_field.get("city")
                or addr_field.get("cityName")
                or filters.city
                or ""
            )
            neighborhood = (
                addr_field.get("neighborhood")
                or addr_field.get("neighborhoodName")
                or None
            )
            address = f"{street} {house_num}".strip() or None
        else:
            # Flat string address
            address = str(addr_field) if addr_field else None
            city = filters.city or ""
            neighborhood = None

        # Coordinates
        geo = item.get("geolocation") or item.get("coordinates") or {}
        lat = self._safe_float(geo.get("lat") or geo.get("latitude"))
        lng = self._safe_float(geo.get("lng") or geo.get("longitude"))

        # Images
        media = item.get("media") or item.get("images") or []
        images = [
            m["src"] if isinstance(m, dict) else str(m)
            for m in media
            if m
        ]

        title = (
            item.get("title")
            or item.get("description", "")[:80]
            or f"דירה {int(rooms) if rooms else '?'} חדרים ב{city}"
        )

        return RawListing(
            source=self.source_name,
            source_id=item_id,
            original_url=url,
            title=title,
            description=item.get("description"),
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

    def _extract_listings_from_payload(
        self, data: dict[str, Any]
    ) -> tuple[list[dict], int]:
        """
        Walk common Madlan GraphQL response shapes to extract raw listing dicts.
        Returns (items, total_count).
        """
        # Try several known response shapes
        candidates: list[Any] = []
        total = 0

        # Shape 1: data.searchListings.listings / totalListings
        search = (data.get("data") or {}).get("searchListings")
        if isinstance(search, dict):
            candidates = search.get("listings") or search.get("nodes") or []
            total = search.get("totalListings") or search.get("totalCount") or len(candidates)

        # Shape 2: data.area.listings.nodes
        if not candidates:
            area = (data.get("data") or {}).get("area") or {}
            listings_node = area.get("listings") or {}
            if isinstance(listings_node, dict):
                candidates = listings_node.get("nodes") or listings_node.get("listings") or []
                total = listings_node.get("totalCount") or len(candidates)
            elif isinstance(listings_node, list):
                candidates = listings_node
                total = len(candidates)

        # Shape 3: data.listings (flat)
        if not candidates:
            flat = (data.get("data") or {}).get("listings")
            if isinstance(flat, list):
                candidates = flat
                total = len(flat)

        # Shape 4: top-level listings key (non-GraphQL REST fallback)
        if not candidates:
            flat = data.get("listings")
            if isinstance(flat, list):
                candidates = flat
                total = len(flat)

        return candidates, int(total)

    def _parse_response(
        self, data: dict[str, Any], filters: SearchFilters
    ) -> tuple[list[RawListing], int]:
        items, total = self._extract_listings_from_payload(data)

        listings: list[RawListing] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                listing = self._parse_listing(item, filters)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                logger.warning(
                    "Madlan: failed to parse listing %s: %s", item.get("id"), exc
                )

        return listings, total

    # ------------------------------------------------------------------
    # Page fetcher
    # ------------------------------------------------------------------

    async def _fetch_page(
        self,
        context: BrowserContext,
        filters: SearchFilters,
        page_num: int,
    ) -> tuple[list[RawListing], int]:
        captured: list[dict] = []

        async def on_response(response):  # type: ignore[no-untyped-def]
            if _MADLAN_API_FRAGMENT in response.url:
                try:
                    body = await response.json()
                    # Only keep responses that look like listing data
                    if isinstance(body, dict) and body.get("data"):
                        captured.append(body)
                except Exception:
                    pass

        page = await context.new_page()
        page.on("response", on_response)

        url = self._build_url(filters, page_num)
        logger.info("Madlan: fetching page %d → %s", page_num, url)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
        except Exception as exc:
            logger.warning("Madlan: timeout/error on page %d: %s", page_num, exc)
        finally:
            await page.close()

        listings: list[RawListing] = []
        best_total = 0
        for data in captured:
            batch, total = self._parse_response(data, filters)
            listings.extend(batch)
            if total > best_total:
                best_total = total

        return listings, best_total

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    async def scrape(self, filters: SearchFilters) -> list[RawListing]:
        all_listings: list[RawListing] = []
        seen_ids: set[str] = set()

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=settings.playwright_headless)
            context = await browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1440, "height": 900},
                locale="he-IL",
            )
            try:
                page_num = 1
                # Madlan typically has 20-30 listings per page; cap at 20 pages
                max_pages = 20

                while page_num <= max_pages:
                    if filters.max_results and len(all_listings) >= filters.max_results:
                        break

                    batch, total = await self._fetch_page(context, filters, page_num)

                    if not batch:
                        logger.info("Madlan: no listings on page %d, stopping", page_num)
                        break

                    # Deduplicate across pages
                    new_count = 0
                    for listing in batch:
                        if listing.source_id not in seen_ids:
                            seen_ids.add(listing.source_id)
                            all_listings.append(listing)
                            new_count += 1

                    logger.info(
                        "Madlan: page %d → %d new listings (total so far: %d / %d)",
                        page_num,
                        new_count,
                        len(all_listings),
                        total,
                    )

                    # Stop if we've seen everything or the server says there's no more
                    if total and len(all_listings) >= total:
                        break
                    if new_count == 0:
                        break

                    page_num += 1
                    await asyncio.sleep(settings.scraper_request_delay_seconds)
            finally:
                await browser.close()

        if filters.max_results:
            all_listings = all_listings[: filters.max_results]

        logger.info("Madlan: scraped %d listings total", len(all_listings))
        return all_listings
