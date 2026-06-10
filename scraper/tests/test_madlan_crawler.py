"""Offline unit tests for the Madlan crawler's pure parsing layer.

No network or browser — feeds fixture dicts through the parsers and shape walker.

Run:  cd scraper && pytest tests/test_madlan_crawler.py -v
"""

from __future__ import annotations

from unittest.mock import patch

from dirascan.base.crawler import SearchFilters
from dirascan.crawlers.madlan import MadlanCrawler

from tests.fixtures.madlan_payloads import (
    MADLAN_LISTING_FULL,
    MADLAN_LISTING_NO_ID,
    MADLAN_LISTING_PRICE_NESTED,
    MADLAN_LISTING_SQM_AND_ALT_ADDR,
    MADLAN_SHAPE1_NODES_PAYLOAD,
    MADLAN_SHAPE1_PAYLOAD,
    MADLAN_SHAPE2_LIST_PAYLOAD,
    MADLAN_SHAPE2_PAYLOAD,
    MADLAN_SHAPE3_PAYLOAD,
    MADLAN_SHAPE4_PAYLOAD,
    MADLAN_SHAPE_PRIORITY_PAYLOAD,
)

CRAWLER = MadlanCrawler()
FILTERS = SearchFilters(city="תל אביב")


class TestCitySlug:
    def test_known_hebrew(self):
        assert CRAWLER._city_slug("תל אביב") == "תל-אביב-יפו"

    def test_known_english(self):
        assert CRAWLER._city_slug("tel aviv") == "תל-אביב-יפו"

    def test_unknown_hyphenates(self):
        assert CRAWLER._city_slug("כפר קאסם") == "כפר-קאסם"

    def test_empty(self):
        assert CRAWLER._city_slug("") == ""


class TestBuildUrl:
    def test_known_city(self):
        assert CRAWLER._build_url(SearchFilters(city="תל אביב")) == (
            "https://www.madlan.co.il/for-rent/תל-אביב-יפו"
        )

    def test_no_city(self):
        assert CRAWLER._build_url(SearchFilters()) == "https://www.madlan.co.il/for-rent"

    def test_price_params(self):
        url = CRAWLER._build_url(SearchFilters(city="תל אביב", price_min=4000, price_max=8000))
        assert "minPrice=4000" in url
        assert "maxPrice=8000" in url

    def test_rooms_params(self):
        url = CRAWLER._build_url(SearchFilters(rooms_min=2.0, rooms_max=4.0))
        assert "minRooms=2.0" in url
        assert "maxRooms=4.0" in url

    def test_page_2(self):
        url = CRAWLER._build_url(SearchFilters(city="תל אביב"), page=2)
        assert "page=2" in url

    def test_page_1_omitted(self):
        url = CRAWLER._build_url(SearchFilters(city="תל אביב"), page=1)
        assert "page=" not in url


class TestSafeConversions:
    def test_safe_float_int(self):
        assert CRAWLER._safe_float(3) == 3.0

    def test_safe_float_string(self):
        assert CRAWLER._safe_float("3.5") == 3.5

    def test_safe_float_none(self):
        assert CRAWLER._safe_float(None) is None

    def test_safe_float_invalid(self):
        assert CRAWLER._safe_float("abc") is None

    def test_safe_int_float(self):
        assert CRAWLER._safe_int(3.7) == 3

    def test_safe_int_string(self):
        assert CRAWLER._safe_int("5") == 5

    def test_safe_int_none(self):
        assert CRAWLER._safe_int(None) is None

    def test_safe_int_invalid(self):
        assert CRAWLER._safe_int("xyz") is None


class TestParseListing:
    def test_full_dict_address_and_geolocation(self):
        listing = CRAWLER._parse_listing(MADLAN_LISTING_FULL, FILTERS)
        assert listing is not None
        assert listing.source == "madlan"
        assert listing.source_id == "m-001"
        assert listing.original_url == "https://www.madlan.co.il/item/tok-1"
        assert listing.price == 5500
        assert listing.rooms == 3.5
        assert listing.sqm == 75.0
        assert listing.floor == 2
        assert listing.address == "הרצל 5"
        assert listing.city == "תל אביב"
        assert listing.neighborhood == "פלורנטין"
        assert listing.lat == 32.06
        assert listing.lng == 34.77
        assert listing.images == ["https://img.madlan.co.il/1.jpg"]
        assert listing.raw_data is MADLAN_LISTING_FULL

    def test_nested_price_flat_address_coordinates(self):
        listing = CRAWLER._parse_listing(MADLAN_LISTING_PRICE_NESTED, FILTERS)
        assert listing is not None
        assert listing.source_id == "m-002"  # from listingId
        # No token → URL falls back to id.
        assert listing.original_url == "https://www.madlan.co.il/item/m-002"
        assert listing.price == 6000  # nested price.value
        assert listing.price_raw == "6000"
        assert listing.rooms == 4.0
        assert listing.sqm == 90.0  # squareMeters
        assert listing.address == "הרצל 5"  # flat string address
        assert listing.city == "תל אביב"  # falls back to filter
        assert listing.neighborhood is None
        assert listing.lat == 32.07  # coordinates.latitude
        assert listing.lng == 34.78  # coordinates.longitude
        assert listing.images == ["https://img.madlan.co.il/2.jpg"]

    def test_sqm_key_and_alt_address_fields(self):
        listing = CRAWLER._parse_listing(MADLAN_LISTING_SQM_AND_ALT_ADDR, FILTERS)
        assert listing is not None
        assert listing.sqm == 60.0  # via "sqm"
        assert listing.address == "ויצמן 12"  # streetName + streetNumber
        assert listing.city == "חיפה"  # cityName
        assert listing.neighborhood == "הדר"  # neighborhoodName

    def test_no_id_returns_none(self):
        assert CRAWLER._parse_listing(MADLAN_LISTING_NO_ID, FILTERS) is None

    def test_autogenerated_title_when_missing(self):
        listing = CRAWLER._parse_listing(MADLAN_LISTING_PRICE_NESTED, FILTERS)
        # No title/description → "דירה N חדרים ב<city>"
        assert "4" in listing.title and "תל אביב" in listing.title


class TestExtractListingsFromPayload:
    def test_shape1_search_listings(self):
        items, total = CRAWLER._extract_listings_from_payload(MADLAN_SHAPE1_PAYLOAD)
        assert len(items) == 1
        assert total == 42

    def test_shape1_nodes_variant(self):
        items, total = CRAWLER._extract_listings_from_payload(MADLAN_SHAPE1_NODES_PAYLOAD)
        assert len(items) == 1
        assert total == 7

    def test_shape2_area_nodes(self):
        items, total = CRAWLER._extract_listings_from_payload(MADLAN_SHAPE2_PAYLOAD)
        assert len(items) == 1
        assert total == 15

    def test_shape2_area_list(self):
        items, total = CRAWLER._extract_listings_from_payload(MADLAN_SHAPE2_LIST_PAYLOAD)
        assert len(items) == 1
        assert total == 1

    def test_shape3_flat_data_listings(self):
        items, total = CRAWLER._extract_listings_from_payload(MADLAN_SHAPE3_PAYLOAD)
        assert len(items) == 1
        assert total == 1

    def test_shape4_top_level_listings(self):
        items, total = CRAWLER._extract_listings_from_payload(MADLAN_SHAPE4_PAYLOAD)
        assert len(items) == 1
        assert total == 1

    def test_empty_payload(self):
        assert CRAWLER._extract_listings_from_payload({}) == ([], 0)

    def test_shape1_wins_over_shape4(self):
        items, total = CRAWLER._extract_listings_from_payload(MADLAN_SHAPE_PRIORITY_PAYLOAD)
        assert items[0]["id"] == "m-001"  # the searchListings item, not the top-level one
        assert total == 99


class TestParseResponse:
    def test_shape1_end_to_end(self):
        listings, total = CRAWLER._parse_response(MADLAN_SHAPE1_PAYLOAD, FILTERS)
        assert total == 42
        assert len(listings) == 1
        assert listings[0].source_id == "m-001"

    def test_skips_non_dict_items(self):
        payload = {"data": {"listings": ["not-a-dict", MADLAN_LISTING_FULL]}}
        listings, _ = CRAWLER._parse_response(payload, FILTERS)
        assert [l.source_id for l in listings] == ["m-001"]

    def test_bad_item_is_logged_and_skipped(self):
        # media dict without "src" makes _parse_listing raise KeyError — must be caught.
        payload = {"data": {"listings": [{"id": "boom", "media": [{"foo": 1}]}, MADLAN_LISTING_FULL]}}
        with patch("dirascan.crawlers.madlan.logger") as mock_logger:
            listings, _ = CRAWLER._parse_response(payload, FILTERS)
        assert [l.source_id for l in listings] == ["m-001"]
        assert mock_logger.warning.called
