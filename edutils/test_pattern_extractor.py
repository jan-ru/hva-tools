"""Unit tests for PatternExtractor (no browser required)."""

import pytest
from bs4 import BeautifulSoup

from scraping_utils import PatternExtractor


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


extractor = PatternExtractor()


# ---------------------------------------------------------------------------
# extract_time_duration
# ---------------------------------------------------------------------------

class TestExtractTimeDuration:
    def test_hours_and_minutes(self):
        soup = _soup('<span title="2 uren en 30 minuten"></span>')
        assert extractor.extract_time_duration(soup) == 150

    def test_singular_forms(self):
        soup = _soup('<span title="1 uur en 1 minuut"></span>')
        # Default pattern uses uren?/minuten? — singular "uur" won't match.
        # Document expected behaviour: returns None for "uur" singular form.
        assert extractor.extract_time_duration(soup) is None

    def test_zero_hours(self):
        soup = _soup('<span title="0 uren en 45 minuten"></span>')
        assert extractor.extract_time_duration(soup) == 45

    def test_no_match_returns_none(self):
        soup = _soup('<span title="geen tijd beschikbaar"></span>')
        assert extractor.extract_time_duration(soup) is None

    def test_missing_title_returns_none(self):
        soup = _soup('<span>2 uren en 30 minuten</span>')
        assert extractor.extract_time_duration(soup) is None

    def test_multiple_elements_uses_first(self):
        soup = _soup(
            '<span title="1 uren en 0 minuten"></span>'
            '<span title="3 uren en 15 minuten"></span>'
        )
        assert extractor.extract_time_duration(soup) == 60


# ---------------------------------------------------------------------------
# extract_percentage
# ---------------------------------------------------------------------------

class TestExtractPercentage:
    def test_custom_pattern(self):
        soup = _soup('<div title="voortgang van 72%"></div>')
        assert extractor.extract_percentage(soup, r'voortgang van (\d+)%') == 72

    def test_default_pattern(self):
        soup = _soup('<div title="50%"></div>')
        assert extractor.extract_percentage(soup) == 50

    def test_no_match_returns_none(self):
        soup = _soup('<div title="geen percentage"></div>')
        assert extractor.extract_percentage(soup, r'voortgang van (\d+)%') is None

    def test_zero_percent(self):
        soup = _soup('<div title="voortgang van 0%"></div>')
        assert extractor.extract_percentage(soup, r'voortgang van (\d+)%') == 0

    def test_hundred_percent(self):
        soup = _soup('<div title="voortgang van 100%"></div>')
        assert extractor.extract_percentage(soup, r'voortgang van (\d+)%') == 100


# ---------------------------------------------------------------------------
# extract_completion_ratio
# ---------------------------------------------------------------------------

class TestExtractCompletionRatio:
    def test_basic_ratio(self):
        soup = _soup('<div title="5 van de 10 opdrachten"></div>')
        completed, total, pct = extractor.extract_completion_ratio(soup, "opdrachten")
        assert completed == 5
        assert total == 10
        assert pct == pytest.approx(50.0)

    def test_full_completion(self):
        soup = _soup('<div title="10 van de 10 quizzen"></div>')
        completed, total, pct = extractor.extract_completion_ratio(soup, "quizzen")
        assert completed == 10
        assert total == 10
        assert pct == pytest.approx(100.0)

    def test_zero_completed(self):
        soup = _soup('<div title="0 van de 8 opdrachten"></div>')
        completed, total, pct = extractor.extract_completion_ratio(soup, "opdrachten")
        assert completed == 0
        assert total == 8
        assert pct == pytest.approx(0.0)

    def test_zero_total_avoids_division_by_zero(self):
        soup = _soup('<div title="0 van de 0 opdrachten"></div>')
        completed, total, pct = extractor.extract_completion_ratio(soup, "opdrachten")
        assert completed == 0
        assert total == 0
        assert pct == pytest.approx(0.0)

    def test_no_match_returns_nones(self):
        soup = _soup('<div title="geen data"></div>')
        assert extractor.extract_completion_ratio(soup, "opdrachten") == (None, None, None)

    def test_wrong_item_type_returns_nones(self):
        soup = _soup('<div title="5 van de 10 opdrachten"></div>')
        assert extractor.extract_completion_ratio(soup, "quizzen") == (None, None, None)


# ---------------------------------------------------------------------------
# extract_select_options
# ---------------------------------------------------------------------------

class TestExtractSelectOptions:
    def test_extracts_options(self):
        soup = _soup(
            '<select id="mySelect">'
            '  <option value="">-- Kies --</option>'
            '  <option value="1">Module A</option>'
            '  <option value="2">Module B</option>'
            '</select>'
        )
        options = extractor.extract_select_options(soup, "#mySelect")
        assert options == [
            {"value": "1", "name": "Module A"},
            {"value": "2", "name": "Module B"},
        ]

    def test_empty_value_options_are_skipped(self):
        soup = _soup(
            '<select id="s">'
            '  <option value="">Selecteer</option>'
            '</select>'
        )
        assert extractor.extract_select_options(soup, "#s") == []

    def test_missing_select_returns_empty_list(self):
        soup = _soup('<div></div>')
        assert extractor.extract_select_options(soup, "#nonexistent") == []
