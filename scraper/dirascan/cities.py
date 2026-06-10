"""Canonical city data for DiraScan.

Single source of truth for:
- the list of cities the UI offers (``CANONICAL_CITIES``, Hebrew display names),
- the Yad2 numeric city codes (``CITY_TO_YAD2_CODE``),
- the Madlan URL slugs (``CITY_TO_MADLAN_SLUG``).

The crawlers import the lookup dicts from here instead of defining their own, so
the supported-city set never drifts between scraping and the UI.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Yad2 numeric city codes (Hebrew names + English transliterations)
# ---------------------------------------------------------------------------

CITY_TO_YAD2_CODE: dict[str, str] = {
    # Hebrew names
    "תל אביב": "5000",
    "תל אביב יפו": "5000",
    "ירושלים": "3000",
    "חיפה": "4000",
    "ראשון לציון": "8300",
    "פתח תקווה": "7900",
    "אשדוד": "6400",
    "נתניה": "7400",
    "באר שבע": "9000",
    "בני ברק": "7100",
    "חולון": "6200",
    "רמת גן": "5300",
    "גבעתיים": "5200",
    "הרצליה": "6600",
    "כפר סבא": "7300",
    "רחובות": "8400",
    "אשקלון": "6300",
    "בת ים": "6700",
    "מודיעין": "7000",
    "מודיעין מכבים רעות": "7000",
    "לוד": "7600",
    "רמלה": "8100",
    "נס ציונה": "7500",
    "רעננה": "8200",
    "הוד השרון": "6900",
    "רמת השרון": "8250",
    "קריית גת": "9700",
    "עפולה": "9500",
    "כרמיאל": "9200",
    # English transliterations
    "tel aviv": "5000",
    "jerusalem": "3000",
    "haifa": "4000",
    "rishon lezion": "8300",
    "rishon le-zion": "8300",
    "petah tikva": "7900",
    "ashdod": "6400",
    "netanya": "7400",
    "beer sheva": "9000",
    "beersheba": "9000",
    "bnei brak": "7100",
    "holon": "6200",
    "ramat gan": "5300",
    "givatayim": "5200",
    "herzliya": "6600",
    "kfar saba": "7300",
    "rehovot": "8400",
    "ashkelon": "6300",
    "bat yam": "6700",
    "modiin": "7000",
    "lod": "7600",
    "ramla": "8100",
    "nes ziona": "7500",
    "raanana": "8200",
    "hod hasharon": "6900",
}

# ---------------------------------------------------------------------------
# Madlan URL slugs (Hebrew text used directly in the path)
# ---------------------------------------------------------------------------

CITY_TO_MADLAN_SLUG: dict[str, str] = {
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

# ---------------------------------------------------------------------------
# Canonical Hebrew display names offered by the UI (roughly population order).
# One entry per city — duplicate display variants (e.g. "תל אביב יפו") are
# collapsed to the common short form.
# ---------------------------------------------------------------------------

CANONICAL_CITIES: list[str] = [
    "תל אביב",
    "ירושלים",
    "חיפה",
    "ראשון לציון",
    "פתח תקווה",
    "אשדוד",
    "נתניה",
    "באר שבע",
    "בני ברק",
    "חולון",
    "רמת גן",
    "גבעתיים",
    "הרצליה",
    "כפר סבא",
    "רחובות",
    "אשקלון",
    "בת ים",
    "מודיעין",
    "לוד",
    "רמלה",
    "נס ציונה",
    "רעננה",
    "הוד השרון",
    "רמת השרון",
    "קריית גת",
    "עפולה",
    "כרמיאל",
]
