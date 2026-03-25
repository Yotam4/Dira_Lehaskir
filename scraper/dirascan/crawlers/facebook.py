from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from dirascan.base.crawler import BaseCrawler, RawListing, SearchFilters
from dirascan.nlp.hebrew import extract_all
from dirascan.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known Israeli apartment rental Facebook group IDs / slugs.
# Add more groups as needed.
# ---------------------------------------------------------------------------

DEFAULT_GROUPS: list[str] = [
    "dira.lehaskir.tlv",           # דירות להשכרה תל אביב
    "1612953322326656",             # דירות להשכרה - תל אביב והמרכז
    "rentapartmentisrael",          # Rent Apartment Israel
    "385058245034222",              # דירות להשכרה ירושלים
    "dirajerusalem",
]

_POSTS_PER_PAGE = 50
_DEFAULT_PAGES = 5  # number of "scroll pages" per group


def _scrape_group_sync(
    group_id: str,
    pages: int,
    credentials: tuple[str, str] | None,
    options: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Synchronous wrapper around facebook-scraper's get_posts().
    Runs in a thread executor so as not to block the event loop.
    """
    try:
        from facebook_scraper import get_posts  # type: ignore[import]
    except ImportError:
        logger.error("facebook-scraper is not installed. Run: pip install facebook-scraper")
        return []

    posts: list[dict[str, Any]] = []
    try:
        kwargs: dict[str, Any] = {"pages": pages, "options": options}
        if credentials:
            kwargs["credentials"] = credentials

        for post in get_posts(group_id, **kwargs):
            posts.append(post)
    except Exception as exc:
        logger.warning("Facebook: error scraping group %s: %s", group_id, exc)

    return posts


def _city_mentioned(text: str, city: str) -> bool:
    """Return True if the city name (or common short forms) appears in the post."""
    if not city:
        return True  # no city filter → accept all
    text_lower = text.lower()
    city_lower = city.lower().strip()

    # Direct match
    if city_lower in text_lower:
        return True

    # Common Hebrew city aliases
    aliases: dict[str, list[str]] = {
        "תל אביב": ["ת\"א", "ת.א", "תל-אביב", "tel aviv", "tlv"],
        "תל אביב יפו": ["ת\"א", "ת.א", "תל-אביב", "tel aviv", "tlv"],
        "ירושלים": ["י-ם", "ירושלם", "jerusalem", "jlm"],
        "חיפה": ["haifa", "חיפא"],
        "באר שבע": ["ב\"ש", "ב.ש", "beer sheva", "beersheba"],
        "רמת גן": ["ר\"ג", "ר.ג", "ramat gan"],
        "גבעתיים": ["givatayim"],
        "הרצליה": ["herzliya"],
        "פתח תקווה": ["פ\"ת", "פ.ת", "petah tikva"],
        "ראשון לציון": ["ראשל\"צ", "rishon lezion"],
        "נתניה": ["netanya"],
        "אשדוד": ["ashdod"],
        "חולון": ["holon"],
        "בת ים": ["bat yam"],
    }
    for alt in aliases.get(city, []):
        if alt.lower() in text_lower:
            return True

    return False


def _neighborhood_mentioned(text: str, neighborhoods: list[str]) -> bool:
    """Return True if any neighborhood from the filter appears in the post text."""
    if not neighborhoods:
        return True
    text_lower = text.lower()
    return any(n.lower() in text_lower for n in neighborhoods)


class FacebookCrawler(BaseCrawler):
    """
    Scraper for Facebook group rental posts.

    Uses the ``facebook-scraper`` library (cookie/credential-based) to
    fetch posts from configured groups, then applies Hebrew NLP regex
    extractors to pull out price, rooms, floor, and sqm.

    Configuration:
    - Set FACEBOOK_EMAIL + FACEBOOK_PASSWORD in .env for authenticated access.
    - Override GROUP_IDS on a subclass or pass groups via ``extra_groups``.
    """

    source_name = "facebook"

    # Override at runtime or on a subclass to target specific groups
    GROUP_IDS: list[str] = list(DEFAULT_GROUPS)

    def __init__(self, extra_groups: list[str] | None = None) -> None:
        super().__init__()
        self._groups = list(self.GROUP_IDS)
        if extra_groups:
            self._groups.extend(extra_groups)

    # ------------------------------------------------------------------
    # Post → RawListing conversion
    # ------------------------------------------------------------------

    def _post_to_listing(
        self,
        post: dict[str, Any],
        filters: SearchFilters,
        crawl_run_id: uuid.UUID | None = None,
    ) -> RawListing | None:
        post_id = str(post.get("post_id") or post.get("id") or "")
        if not post_id:
            return None

        text: str = (
            post.get("post_text")
            or post.get("text")
            or post.get("message")
            or ""
        )
        if not text:
            return None

        # City / neighborhood filter
        if not _city_mentioned(text, filters.city):
            return None
        if filters.neighborhoods and not _neighborhood_mentioned(text, filters.neighborhoods):
            return None

        # Hebrew NLP extraction
        extracted = extract_all(text)
        price: int | None = extracted.get("price")
        rooms: float | None = extracted.get("rooms")
        sqm: float | None = extracted.get("sqm")
        floor: int | None = extracted.get("floor")
        phone: str | None = extracted.get("phone")

        # Price range filter (skip if clearly outside)
        if price is not None:
            if filters.price_min and price < filters.price_min:
                return None
            if filters.price_max and price > filters.price_max:
                return None

        # Rooms filter
        if rooms is not None:
            if filters.rooms_min and rooms < filters.rooms_min:
                return None
            if filters.rooms_max and rooms > filters.rooms_max:
                return None

        # Images — facebook-scraper returns either a list of strings or dicts with "src"
        images: list[str] = []
        raw_images = post.get("images") or []
        if isinstance(raw_images, list):
            for img in raw_images:
                if isinstance(img, str):
                    images.append(img)
                elif isinstance(img, dict) and img.get("src"):
                    images.append(img["src"])

        # Source URL
        post_url: str | None = post.get("post_url") or post.get("link")

        # Use first 120 chars of text as title
        title = text[:120].replace("\n", " ").strip()

        return RawListing(
            source=self.source_name,
            source_id=post_id,
            original_url=post_url,
            title=title,
            description=text,
            price_raw=str(price) if price else None,
            price=price,
            rooms_raw=str(rooms) if rooms else None,
            rooms=rooms,
            sqm_raw=str(sqm) if sqm else None,
            sqm=sqm,
            floor_raw=str(floor) if floor else None,
            floor=floor,
            phone=phone,
            address=None,
            city=filters.city or "",
            neighborhood=None,
            lat=None,
            lng=None,
            images=images,
            raw_data=post,
            crawl_run_id=crawl_run_id,
        )

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    async def scrape(self, filters: SearchFilters) -> list[RawListing]:
        if not self._groups:
            logger.warning("Facebook: no groups configured — nothing to scrape")
            return []

        credentials: tuple[str, str] | None = None
        if settings.facebook_email and settings.facebook_password:
            credentials = (settings.facebook_email, settings.facebook_password)
        else:
            logger.warning(
                "Facebook: FACEBOOK_EMAIL / FACEBOOK_PASSWORD not set. "
                "Scraping public groups without authentication (may be limited)."
            )

        options: dict[str, Any] = {
            "posts_per_page": _POSTS_PER_PAGE,
            "allow_extra_requests": False,
        }

        all_listings: list[RawListing] = []
        seen_ids: set[str] = set()

        for group_id in self._groups:
            if filters.max_results and len(all_listings) >= filters.max_results:
                break

            logger.info("Facebook: scraping group %s", group_id)

            posts = await asyncio.to_thread(
                _scrape_group_sync,
                group_id,
                _DEFAULT_PAGES,
                credentials,
                options,
            )

            logger.info("Facebook: fetched %d posts from group %s", len(posts), group_id)

            for post in posts:
                if filters.max_results and len(all_listings) >= filters.max_results:
                    break

                try:
                    listing = self._post_to_listing(post, filters)
                    if listing and listing.source_id not in seen_ids:
                        seen_ids.add(listing.source_id)
                        all_listings.append(listing)
                except Exception as exc:
                    logger.warning(
                        "Facebook: failed to parse post %s: %s",
                        post.get("post_id"),
                        exc,
                    )

            # Polite delay between groups
            await asyncio.sleep(settings.scraper_request_delay_seconds)

        if filters.max_results:
            all_listings = all_listings[: filters.max_results]

        logger.info("Facebook: scraped %d listings total", len(all_listings))
        return all_listings
