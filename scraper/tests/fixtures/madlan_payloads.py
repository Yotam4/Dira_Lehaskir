"""Madlan GraphQL/REST payloads.

The Madlan crawler intercepts ``madlan.co.il/api`` responses and walks several
known shapes in ``MadlanCrawler._extract_listings_from_payload``. The listing
dicts target the field variations handled by ``MadlanCrawler._parse_listing``.
"""

from __future__ import annotations

# Nested address dict, geolocation (lat/lng), plain-int price, media as dicts,
# sqm via ``size``, id + token.
MADLAN_LISTING_FULL = {
    "id": "m-001",
    "token": "tok-1",
    "price": 5500,
    "rooms": 3.5,
    "size": 75,
    "floor": 2,
    "address": {
        "street": "הרצל",
        "houseNumber": "5",
        "city": "תל אביב",
        "neighborhood": "פלורנטין",
    },
    "geolocation": {"lat": 32.06, "lng": 34.77},
    "media": [{"src": "https://img.madlan.co.il/1.jpg"}, None],
    "title": "דירה",
    "description": "תיאור הדירה",
}

# Nested price dict, coordinates (latitude/longitude), images as list-of-str,
# listingId instead of id, sqm via ``squareMeters``, flat string address.
MADLAN_LISTING_PRICE_NESTED = {
    "listingId": "m-002",
    "price": {"value": 6000, "currency": "ILS"},
    "rooms": 4,
    "squareMeters": 90,
    "address": "הרצל 5",
    "coordinates": {"latitude": 32.07, "longitude": 34.78},
    "images": ["https://img.madlan.co.il/2.jpg"],
}

# sqm via the ``sqm`` key; streetName/streetNumber/cityName/neighborhoodName
# address variant.
MADLAN_LISTING_SQM_AND_ALT_ADDR = {
    "id": "m-003",
    "price": 4800,
    "rooms": 2,
    "sqm": 60,
    "address": {
        "streetName": "ויצמן",
        "streetNumber": "12",
        "cityName": "חיפה",
        "neighborhoodName": "הדר",
    },
}

# No id and no listingId → _parse_listing returns None.
MADLAN_LISTING_NO_ID = {"price": 5000, "rooms": 3}

# --- Response-shape envelopes ------------------------------------------------

# Shape 1: data.searchListings.listings + totalListings
MADLAN_SHAPE1_PAYLOAD = {
    "data": {
        "searchListings": {
            "listings": [MADLAN_LISTING_FULL],
            "totalListings": 42,
        }
    }
}

# Shape 1 variant: ``nodes`` key + totalCount
MADLAN_SHAPE1_NODES_PAYLOAD = {
    "data": {
        "searchListings": {
            "nodes": [MADLAN_LISTING_FULL],
            "totalCount": 7,
        }
    }
}

# Shape 2: data.area.listings.nodes + totalCount
MADLAN_SHAPE2_PAYLOAD = {
    "data": {
        "area": {
            "listings": {
                "nodes": [MADLAN_LISTING_FULL],
                "totalCount": 15,
            }
        }
    }
}

# Shape 2 variant: data.area.listings is itself a list
MADLAN_SHAPE2_LIST_PAYLOAD = {
    "data": {"area": {"listings": [MADLAN_LISTING_FULL]}}
}

# Shape 3: data.listings flat list
MADLAN_SHAPE3_PAYLOAD = {"data": {"listings": [MADLAN_LISTING_FULL]}}

# Shape 4: top-level listings key (non-GraphQL REST fallback)
MADLAN_SHAPE4_PAYLOAD = {"listings": [MADLAN_LISTING_FULL]}

# Satisfies both shape 1 and shape 4 — shape 1 must win (tried first).
MADLAN_SHAPE_PRIORITY_PAYLOAD = {
    "data": {
        "searchListings": {
            "listings": [MADLAN_LISTING_FULL],
            "totalListings": 99,
        }
    },
    "listings": [MADLAN_LISTING_PRICE_NESTED],
}
