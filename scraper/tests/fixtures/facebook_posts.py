"""Facebook group post dicts, shaped like ``facebook-scraper`` output.

These drive ``FacebookCrawler._post_to_listing`` and the module-level
``_city_mentioned`` / ``_neighborhood_mentioned`` helpers. The Hebrew text uses
ASCII quotes (e.g. ``ש"ח``, ``מ"ר``) so the Hebrew NLP regexes in
``dirascan.nlp.hebrew`` actually match.
"""

from __future__ import annotations

# Every extractable field present: rooms 3, floor 2, sqm 75, price 5500,
# phone, city תל אביב, images as strings.
FB_POST_WITH_ALL_FIELDS = {
    "post_id": "fb-001",
    "post_text": 'דירת 3 חדרים ברחוב דיזנגוף, קומה 2, 75 מ"ר, 5500 ש"ח לחודש, '
    "להתקשר 054-123-4567, תל אביב",
    "post_url": "https://facebook.com/groups/x/posts/fb-001",
    "images": ["https://scontent.fb/1.jpg", "https://scontent.fb/2.jpg"],
}

# City via alias ת"א (not the literal "תל אביב").
FB_POST_CITY_ALIAS = {
    "post_id": "fb-002",
    "post_text": 'דירת 2 חדרים בת"א, 4500 ש"ח לחודש',
    "post_url": "https://facebook.com/groups/x/posts/fb-002",
}

# Wrong city — should be filtered out when filtering for תל אביב.
FB_POST_WRONG_CITY = {
    "post_id": "fb-003",
    "post_text": 'דירה להשכרה בחיפה, 4000 ש"ח לחודש',
}

# Clearly high price (12000) — used for price-range filter tests.
FB_POST_HIGH_PRICE = {
    "post_id": "fb-004",
    "post_text": 'דירת 4 חדרים, 12000 ש"ח לחודש, תל אביב',
}

# Single room (1.0) — used for rooms filter tests.
FB_POST_LOW_ROOMS = {
    "post_id": "fb-005",
    "post_text": 'דירת 1 חדר, 3000 ש"ח לחודש, תל אביב',
}

# Images as dicts with "src".
FB_POST_IMAGES_AS_DICTS = {
    "post_id": "fb-006",
    "post_text": 'דירת 3 חדרים, 5000 ש"ח לחודש, תל אביב',
    "images": [{"src": "https://scontent.fb/a.jpg"}, {"no_src": "x"}, "https://scontent.fb/b.jpg"],
}

# Uses "id"/"link"/"text" keys instead of post_id/post_url/post_text.
FB_POST_ALT_KEYS = {
    "id": "fb-007",
    "text": 'דירת 3 חדרים, 5200 ש"ח לחודש, תל אביב',
    "link": "https://facebook.com/groups/x/posts/fb-007",
}

# No id at all → returns None.
FB_POST_NO_ID = {"post_text": 'דירה, 5000 ש"ח, תל אביב'}

# Empty text → returns None.
FB_POST_NO_TEXT = {"post_id": "fb-009", "post_text": ""}

# Mentions a neighborhood (פלורנטין) — for neighborhood filter tests.
FB_POST_WITH_NEIGHBORHOOD = {
    "post_id": "fb-010",
    "post_text": 'דירת 2 חדרים בפלורנטין, 5500 ש"ח לחודש, תל אביב',
}
