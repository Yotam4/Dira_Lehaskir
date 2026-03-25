"""
Hebrew free-text extraction helpers for Facebook group posts.

Facebook posts are unstructured Hebrew text.  These regex-based extractors
pull out price, room count, floor, and sqm from typical post patterns.

Example post:
    "דירת 3 חדרים ברחוב דיזנגוף, קומה 2, 75 מ״ר, 5500 ש״ח לחודש, זמינה מיידית"
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Price extraction — returns ILS integer or None
# ---------------------------------------------------------------------------

_PRICE_PATTERNS = [
    r"(\d[\d,\.]+)\s*(?:ש[\"׳]ח|שח|₪|ils)",
    r"(?:מחיר|שכ[\"׳]ד|שכירות)[:\s]+(\d[\d,\.]+)",
    r"(\d[\d,\.]+)\s*(?:לחודש|בחודש|ח[\"׳]ל)",
    # Price range "5500-6000 ₪" → extract lower bound
    r"(\d[\d,\.]+)-\d[\d,\.]+\s*(?:ש[\"׳]ח|שח|₪|לחודש|בחודש)",
    # No-separator: "מחיר5500" (keyword immediately followed by digits)
    r"(?:מחיר|שכ[\"׳]ד|שכירות)(\d[\d,\.]+)",
]


def extract_price(text: str) -> int | None:
    for pattern in _PRICE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", "").replace(".", "")
            try:
                return int(raw)
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Room extraction — returns float or None (3.5 חדרים is common)
# ---------------------------------------------------------------------------

_ROOMS_PATTERNS = [
    r"([\d]+(?:[.,][\d]+)?)\s*חד(?:רים|ר)",
    r"(?:דירת|דירה)\s+([\d]+(?:[.,][\d]+)?)",
    r"([\d]+(?:[.,][\d]+)?)\s*rooms",
]


def extract_rooms(text: str) -> float | None:
    for pattern in _ROOMS_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", ".")
            try:
                return float(raw)
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Sqm extraction — returns float or None
# ---------------------------------------------------------------------------

_SQM_PATTERNS = [
    r"([\d]+(?:[.,][\d]+)?)\s*מ[\"׳]?ר",
    r"([\d]+(?:[.,][\d]+)?)\s*(?:sqm|m²|מטר)",
]


def extract_sqm(text: str) -> float | None:
    for pattern in _SQM_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", ".")
            try:
                return float(raw)
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Floor extraction — returns int or None
# ---------------------------------------------------------------------------

_FLOOR_PATTERNS = [
    r"קומה\s+([\d]+)",
    r"([\d]+)\s*\/\s*[\d]+",   # e.g. "3/6" (floor/total)
    r"floor\s+([\d]+)",
]


def extract_floor(text: str) -> int | None:
    for pattern in _FLOOR_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Phone extraction — returns normalised Israeli phone number or None
# ---------------------------------------------------------------------------

_PHONE_PATTERNS = [
    r"0[5][0-9][-\s]?\d{3}[-\s]?\d{4}",   # Israeli mobile: 05X-XXX-XXXX
    r"0[23489][-\s]?\d{7}",                  # Israeli landline: 0X-XXXXXXX
]


def extract_phone(text: str) -> str | None:
    for pattern in _PHONE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            # Normalise: collapse spaces, keep dashes
            return re.sub(r"\s+", "", match.group(0))
    return None


# ---------------------------------------------------------------------------
# Convenience: extract all fields at once
# ---------------------------------------------------------------------------

def extract_all(text: str) -> dict:
    return {
        "price": extract_price(text),
        "rooms": extract_rooms(text),
        "sqm": extract_sqm(text),
        "floor": extract_floor(text),
        "phone": extract_phone(text),
    }
