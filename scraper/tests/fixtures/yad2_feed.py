"""Yad2 feed payloads.

The Yad2 crawler intercepts JSON from ``gw.yad2.co.il/feed-search-legato`` and
navigates ``data["data"]["feed"]["feed_items"]`` (see ``Yad2Crawler._parse_response``).
Each item below targets a specific branch in ``Yad2Crawler._parse_item``.
"""

from __future__ import annotations

# Fully-populated "ad" item — every field present and well-typed.
YAD2_ITEM_COMPLETE = {
    "type": "ad",
    "id": "item-001",
    "link_token": "token-abc",
    "price": 5500,
    "rooms": 3.0,
    "square_meters": 75,
    "floor": 2,
    "coordinates": {"latitude": 32.08, "longitude": 34.78},
    "street": "דיזנגוף",
    "house_number": "1",
    "city_text": "תל אביב",
    "neighborhood_text": "לב העיר",
    "images": [{"src": "https://img.yad2.co.il/1.jpg"}, {"no_src": "x"}],
    "title": "דירה מהממת",
    "description": "תיאור הדירה",
}

# Price/rooms/sqm arrive as strings — exercises the string-coercion branches.
YAD2_ITEM_PRICE_STRING = {
    "type": "ad",
    "id": "item-002",
    "price": "5,500",
    "rooms": "3.5",
    "square_meters": "80",
    "floor": "3",
    "coordinates": {"latitude": 32.1, "longitude": 34.8},
    "street": "אבן גבירול",
    "house_number": "10",
    "city_text": "תל אביב",
    "neighborhood_text": "הצפון הישן",
    "images": [],
}

# Separator / non-ad with no id → _parse_item returns None.
YAD2_ITEM_SEPARATOR = {"type": "separator"}

# Non-ad type but carries an id → still parsed (not skipped).
YAD2_ITEM_PROMOTED_WITH_ID = {
    "type": "promoted_banner",
    "id": "item-004",
    "price": 7000,
    "rooms": 4,
    "city_text": "תל אביב",
}

# Missing coordinates entirely → lat/lng become None.
YAD2_ITEM_NO_COORDS = {
    "type": "ad",
    "id": "item-005",
    "price": 4000,
    "rooms": 2,
    "street": "הרצל",
    "city_text": "תל אביב",
}

# Unparseable numerics + no title → robustness/None-handling + title autogen.
YAD2_ITEM_INVALID_FIELDS = {
    "type": "ad",
    "id": "item-006",
    "price": "יצירת קשר",
    "rooms": 2.5,
    "square_meters": "abc",
    "floor": "קרקע",
    "city_text": "תל אביב",
}

# Full feed payload: 6 items, 5 parseable (separator is dropped).
YAD2_FEED_PAYLOAD = {
    "data": {
        "feed": {
            "total_pages": 3,
            "feed_items": [
                YAD2_ITEM_COMPLETE,
                YAD2_ITEM_PRICE_STRING,
                YAD2_ITEM_SEPARATOR,
                YAD2_ITEM_PROMOTED_WITH_ID,
                YAD2_ITEM_NO_COORDS,
                YAD2_ITEM_INVALID_FIELDS,
            ],
        }
    }
}

YAD2_FEED_PAYLOAD_EMPTY = {"data": {"feed": {"total_pages": 1, "feed_items": []}}}
