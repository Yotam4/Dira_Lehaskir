"""Offline unit tests for the Yad2 crawler's pure parsing layer.

No network or browser — feeds fixture dicts straight through the parsers.

Run:  cd scraper && pytest tests/test_yad2_crawler.py -v
"""

from __future__ import annotations

from unittest.mock import patch

from dirascan.base.crawler import SearchFilters
from dirascan.crawlers.yad2 import Yad2Crawler

from tests.fixtures.yad2_feed import (
    YAD2_FEED_PAYLOAD,
    YAD2_FEED_PAYLOAD_EMPTY,
    YAD2_ITEM_COMPLETE,
    YAD2_ITEM_INVALID_FIELDS,
    YAD2_ITEM_NO_COORDS,
    YAD2_ITEM_PRICE_STRING,
    YAD2_ITEM_PROMOTED_WITH_ID,
    YAD2_ITEM_SEPARATOR,
)

CRAWLER = Yad2Crawler()
FILTERS = SearchFilters(city="תל אביב")


class TestCityCode:
    def test_hebrew(self):
        assert CRAWLER._city_code("תל אביב") == "5000"

    def test_english(self):
        assert CRAWLER._city_code("tel aviv") == "5000"

    def test_unknown(self):
        assert CRAWLER._city_code("NoSuchCity") is None

    def test_empty(self):
        assert CRAWLER._city_code("") is None

    def test_strips_whitespace(self):
        assert CRAWLER._city_code("  ירושלים  ") == "3000"


class TestBuildUrl:
    def test_city_only(self):
        url = CRAWLER._build_url(SearchFilters(city="תל אביב"))
        assert "city=5000" in url
        assert "page=" not in url

    def test_unknown_city_has_no_city_param(self):
        url = CRAWLER._build_url(SearchFilters(city="NoSuchCity"))
        assert "city=" not in url

    def test_rooms_range(self):
        url = CRAWLER._build_url(SearchFilters(city="תל אביב", rooms_min=2, rooms_max=4))
        assert "rooms=2-4" in url

    def test_rooms_partial_defaults_min(self):
        url = CRAWLER._build_url(SearchFilters(rooms_max=3))
        assert "rooms=1-3" in url

    def test_price_range(self):
        url = CRAWLER._build_url(SearchFilters(price_min=4000, price_max=8000))
        assert "price=4000-8000" in url

    def test_price_partial_defaults_max(self):
        url = CRAWLER._build_url(SearchFilters(price_min=4000))
        assert "price=4000-99999" in url

    def test_page_2_present(self):
        url = CRAWLER._build_url(SearchFilters(city="תל אביב"), page=2)
        assert "page=2" in url

    def test_page_1_omitted(self):
        url = CRAWLER._build_url(SearchFilters(city="תל אביב"), page=1)
        assert "page=" not in url


class TestParseItem:
    def test_complete(self):
        listing = CRAWLER._parse_item(YAD2_ITEM_COMPLETE, FILTERS)
        assert listing is not None
        assert listing.source == "yad2"
        assert listing.source_id == "item-001"
        assert listing.original_url == "https://www.yad2.co.il/item/token-abc"
        assert listing.price == 5500
        assert listing.rooms == 3.0
        assert isinstance(listing.rooms, float)
        assert listing.sqm == 75.0
        assert listing.floor == 2
        assert listing.lat == 32.08
        assert listing.lng == 34.78
        assert listing.address == "דיזנגוף 1"
        assert listing.city == "תל אביב"
        assert listing.neighborhood == "לב העיר"
        assert listing.title == "דירה מהממת"
        assert listing.description == "תיאור הדירה"
        # The dict without a "src" key is filtered out.
        assert listing.images == ["https://img.yad2.co.il/1.jpg"]
        assert listing.raw_data is YAD2_ITEM_COMPLETE

    def test_price_string_with_commas(self):
        listing = CRAWLER._parse_item(YAD2_ITEM_PRICE_STRING, FILTERS)
        assert listing is not None
        assert listing.price == 5500
        assert listing.price_raw == "5,500"
        assert listing.rooms == 3.5
        assert listing.sqm == 80.0
        assert listing.floor == 3

    def test_separator_returns_none(self):
        assert CRAWLER._parse_item(YAD2_ITEM_SEPARATOR, FILTERS) is None

    def test_non_ad_type_with_id_is_parsed(self):
        listing = CRAWLER._parse_item(YAD2_ITEM_PROMOTED_WITH_ID, FILTERS)
        assert listing is not None
        assert listing.source_id == "item-004"
        # No link_token → URL falls back to the id.
        assert listing.original_url == "https://www.yad2.co.il/item/item-004"
        # No title supplied → auto-generated from rooms + city.
        assert "4" in listing.title and "תל אביב" in listing.title

    def test_missing_coordinates(self):
        listing = CRAWLER._parse_item(YAD2_ITEM_NO_COORDS, FILTERS)
        assert listing is not None
        assert listing.lat is None
        assert listing.lng is None

    def test_invalid_numeric_fields_become_none(self):
        listing = CRAWLER._parse_item(YAD2_ITEM_INVALID_FIELDS, FILTERS)
        assert listing is not None
        assert listing.price is None  # "יצירת קשר" is not numeric
        assert listing.sqm is None
        assert listing.floor is None
        assert listing.rooms == 2.5

    def test_city_falls_back_to_filter(self):
        item = {"type": "ad", "id": "x", "rooms": 2}
        listing = CRAWLER._parse_item(item, SearchFilters(city="חיפה"))
        assert listing is not None
        assert listing.city == "חיפה"

    def test_empty_id_returns_none(self):
        assert CRAWLER._parse_item({"type": "ad", "id": ""}, FILTERS) is None


class TestParseResponse:
    def test_full_payload(self):
        listings, total_pages = CRAWLER._parse_response(YAD2_FEED_PAYLOAD, FILTERS)
        # 6 items in, separator dropped → 5 listings.
        assert len(listings) == 5
        assert total_pages == 3
        assert all(l.source == "yad2" for l in listings)

    def test_empty_feed(self):
        assert CRAWLER._parse_response(YAD2_FEED_PAYLOAD_EMPTY, FILTERS) == ([], 1)

    def test_missing_data_key(self):
        assert CRAWLER._parse_response({}, FILTERS) == ([], 1)

    def test_missing_feed_key(self):
        assert CRAWLER._parse_response({"data": {}}, FILTERS) == ([], 1)

    def test_bad_item_is_logged_and_skipped(self):
        # images=5 makes _parse_item raise (iterating an int) — must be caught.
        payload = {
            "data": {
                "feed": {
                    "total_pages": 1,
                    "feed_items": [
                        {"type": "ad", "id": "boom", "images": 5},
                        YAD2_ITEM_COMPLETE,
                    ],
                }
            }
        }
        with patch("dirascan.crawlers.yad2.logger") as mock_logger:
            listings, _ = CRAWLER._parse_response(payload, FILTERS)
        # The good item still parses; the bad one is skipped with a warning.
        assert [l.source_id for l in listings] == ["item-001"]
        assert mock_logger.warning.called
