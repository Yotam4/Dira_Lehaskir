"""
Unit tests for Hebrew NLP extractors.
No database or external services required.

Run:  cd scraper && pytest tests/test_nlp.py -v
"""

import pytest
from dirascan.nlp.hebrew import extract_all, extract_floor, extract_price, extract_rooms, extract_sqm


# ---------------------------------------------------------------------------
# extract_price
# ---------------------------------------------------------------------------

class TestExtractPrice:
    def test_shekel_symbol(self):
        assert extract_price("דירה יפה, 4500 ₪ לחודש") == 4500

    def test_shekel_word(self):
        assert extract_price("מחיר: 6,500 ש\"ח") == 6500

    def test_lekhodesh_suffix(self):
        assert extract_price("5800 לחודש, זמינה מיידית") == 5800

    def test_price_label(self):
        assert extract_price("שכירות 7200 לחודש") == 7200

    def test_comma_separated(self):
        assert extract_price("10,500 ש\"ח בחודש") == 10500

    def test_no_price(self):
        assert extract_price("דירת 3 חדרים ברחוב דיזנגוף") is None

    def test_ignores_sqm_numbers(self):
        # 75 should not be mistaken for price when followed by מ"ר
        result = extract_price('75 מ"ר, אין מחיר')
        assert result is None


# ---------------------------------------------------------------------------
# extract_rooms
# ---------------------------------------------------------------------------

class TestExtractRooms:
    def test_whole_rooms(self):
        assert extract_rooms("דירת 3 חדרים") == 3.0

    def test_half_room(self):
        assert extract_rooms("3.5 חדרים קרובה לים") == 3.5

    def test_comma_decimal(self):
        assert extract_rooms("3,5 חדרים") == 3.5

    def test_dira_prefix(self):
        assert extract_rooms("דירה 4 חדרים גדולה") == 4.0

    def test_no_rooms(self):
        assert extract_rooms("דירה יפה, מחיר 4500 ₪") is None


# ---------------------------------------------------------------------------
# extract_sqm
# ---------------------------------------------------------------------------

class TestExtractSqm:
    def test_standard(self):
        assert extract_sqm('75 מ"ר') == 75.0

    def test_without_quotes(self):
        assert extract_sqm("80 מר") == 80.0

    def test_sqm_abbreviation(self):
        assert extract_sqm("90 sqm") == 90.0

    def test_decimal(self):
        assert extract_sqm('67.5 מ"ר') == 67.5

    def test_no_sqm(self):
        assert extract_sqm("דירת 3 חדרים, 4500 ₪") is None


# ---------------------------------------------------------------------------
# extract_floor
# ---------------------------------------------------------------------------

class TestExtractFloor:
    def test_hebrew_floor(self):
        assert extract_floor("קומה 3, נוף לים") == 3

    def test_floor_slash(self):
        assert extract_floor("3/8 קומה") == 3

    def test_english_floor(self):
        assert extract_floor("floor 2, nice view") == 2

    def test_no_floor(self):
        assert extract_floor("דירה יפה, 3 חדרים") is None


# ---------------------------------------------------------------------------
# extract_all — integration
# ---------------------------------------------------------------------------

class TestExtractAll:
    def test_full_post(self):
        text = 'דירת 3 חדרים ברחוב דיזנגוף, קומה 2, 75 מ"ר, 5500 ש"ח לחודש, זמינה מיידית'
        result = extract_all(text)
        assert result["price"] == 5500
        assert result["rooms"] == 3.0
        assert result["sqm"] == 75.0
        assert result["floor"] == 2

    def test_empty_string(self):
        result = extract_all("")
        assert result == {"price": None, "rooms": None, "sqm": None, "floor": None, "phone": None}

    def test_partial_data(self):
        result = extract_all("דירה יפה, 4500 ₪ לחודש")
        assert result["price"] == 4500
        assert result["rooms"] is None
        assert result["sqm"] is None
        assert result["floor"] is None
