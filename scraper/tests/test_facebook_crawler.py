"""Offline unit tests for the Facebook crawler's pure parsing layer.

No network — drives the city/neighborhood matchers and the post→listing
converter (which integrates the Hebrew NLP extractors) with fixture dicts.

Run:  cd scraper && pytest tests/test_facebook_crawler.py -v
"""

from __future__ import annotations

from dirascan.base.crawler import SearchFilters
from dirascan.crawlers.facebook import (
    FacebookCrawler,
    _city_mentioned,
    _neighborhood_mentioned,
)

from tests.fixtures.facebook_posts import (
    FB_POST_ALT_KEYS,
    FB_POST_CITY_ALIAS,
    FB_POST_HIGH_PRICE,
    FB_POST_IMAGES_AS_DICTS,
    FB_POST_LOW_ROOMS,
    FB_POST_NO_ID,
    FB_POST_NO_TEXT,
    FB_POST_WITH_ALL_FIELDS,
    FB_POST_WITH_NEIGHBORHOOD,
    FB_POST_WRONG_CITY,
)

CRAWLER = FacebookCrawler()
TLV = SearchFilters(city="תל אביב")


class TestCityMentioned:
    def test_direct_match(self):
        assert _city_mentioned("דירה בתל אביב", "תל אביב") is True

    def test_alias_ta(self):
        assert _city_mentioned('דירה בת"א, 3 חדרים', "תל אביב") is True

    def test_alias_tlv_english(self):
        assert _city_mentioned("apartment in tlv", "תל אביב") is True

    def test_case_insensitive(self):
        assert _city_mentioned("TEL AVIV apartment", "תל אביב") is True

    def test_no_filter_accepts_all(self):
        assert _city_mentioned("any text", "") is True

    def test_not_mentioned(self):
        assert _city_mentioned("דירה בחיפה", "תל אביב") is False


class TestNeighborhoodMentioned:
    def test_present(self):
        assert _neighborhood_mentioned("דירה בפלורנטין", ["פלורנטין", "יפו"]) is True

    def test_empty_filter_accepts_all(self):
        assert _neighborhood_mentioned("any text", []) is True

    def test_absent(self):
        assert _neighborhood_mentioned("דירה במרכז", ["פלורנטין"]) is False


class TestPostToListing:
    def test_complete_post(self):
        listing = CRAWLER._post_to_listing(FB_POST_WITH_ALL_FIELDS, TLV)
        assert listing is not None
        assert listing.source == "facebook"
        assert listing.source_id == "fb-001"
        assert listing.original_url == "https://facebook.com/groups/x/posts/fb-001"
        assert listing.price == 5500
        assert listing.rooms == 3.0
        assert listing.sqm == 75.0
        assert listing.floor == 2
        assert listing.phone == "054-123-4567"
        assert listing.neighborhood is None
        assert listing.lat is None and listing.lng is None
        assert listing.images == ["https://scontent.fb/1.jpg", "https://scontent.fb/2.jpg"]
        assert listing.description == FB_POST_WITH_ALL_FIELDS["post_text"]
        assert len(listing.title) <= 120
        assert "\n" not in listing.title
        assert listing.raw_data is FB_POST_WITH_ALL_FIELDS

    def test_no_id_returns_none(self):
        assert CRAWLER._post_to_listing(FB_POST_NO_ID, TLV) is None

    def test_no_text_returns_none(self):
        assert CRAWLER._post_to_listing(FB_POST_NO_TEXT, TLV) is None

    def test_wrong_city_filtered_out(self):
        assert CRAWLER._post_to_listing(FB_POST_WRONG_CITY, TLV) is None

    def test_city_alias_accepted(self):
        listing = CRAWLER._post_to_listing(FB_POST_CITY_ALIAS, TLV)
        assert listing is not None
        assert listing.source_id == "fb-002"

    def test_alt_keys(self):
        listing = CRAWLER._post_to_listing(FB_POST_ALT_KEYS, TLV)
        assert listing is not None
        assert listing.source_id == "fb-007"  # from "id"
        assert listing.original_url == "https://facebook.com/groups/x/posts/fb-007"  # from "link"

    def test_price_above_max_filtered(self):
        filters = SearchFilters(city="תל אביב", price_max=8000)
        assert CRAWLER._post_to_listing(FB_POST_HIGH_PRICE, filters) is None

    def test_price_below_min_filtered(self):
        filters = SearchFilters(city="תל אביב", price_min=15000)
        assert CRAWLER._post_to_listing(FB_POST_HIGH_PRICE, filters) is None

    def test_rooms_below_min_filtered(self):
        filters = SearchFilters(city="תל אביב", rooms_min=2.0)
        assert CRAWLER._post_to_listing(FB_POST_LOW_ROOMS, filters) is None

    def test_images_as_dicts(self):
        listing = CRAWLER._post_to_listing(FB_POST_IMAGES_AS_DICTS, TLV)
        assert listing is not None
        # dict with "src" + bare string kept; dict without "src" dropped.
        assert listing.images == ["https://scontent.fb/a.jpg", "https://scontent.fb/b.jpg"]

    def test_neighborhood_filter_match(self):
        filters = SearchFilters(city="תל אביב", neighborhoods=["פלורנטין"])
        listing = CRAWLER._post_to_listing(FB_POST_WITH_NEIGHBORHOOD, filters)
        assert listing is not None
        assert listing.source_id == "fb-010"

    def test_neighborhood_filter_mismatch(self):
        filters = SearchFilters(city="תל אביב", neighborhoods=["נווה צדק"])
        assert CRAWLER._post_to_listing(FB_POST_WITH_NEIGHBORHOOD, filters) is None
