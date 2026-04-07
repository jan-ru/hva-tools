"""Integration test for extract_rubrics using a real Brightspace HTML fixture."""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from brightspace_extractor.extraction import extract_rubrics

FIXTURE = Path(__file__).parent / "rubrics-debug.html"

EXPECTED_RUBRICS = {
    "72528": "Assessment Eindberoepsproduct",
    "72538": "Assessment Eindberoepsproduct 2024-2025 (Individuele herkansing)",
    "72537": "Eindbeoordeling Beroepsproduct",
    "72539": "Eindbeoordeling Beroepsproduct (Individuele herkansing)",
    "72541": "Eindbeoordeling Management Accounting Beroepsproduct",
    "72530": "Eindbeoordeling sprint 1 D & C 2024-2025",
    "72531": "Eindbeoordeling sprint 2 D & C 2024-2025",
    "72532": "Eindbeoordeling sprint 3 D & C 2024-2025",
    "72540": "Herkansing beroepsproduct D&C (Individueel)",
    "72536": "PRO Individueel Portfolio",
    "72529": "Rubric Proces: verslag en gesprek 2025-2026",
    "72533": "Tussentijdse beoordeling Sprint 1 D & C 2025-2026",
    "72534": "Tussentijdse beoordeling sprint 2 D & C 2025-2026",
    "72535": "Tussentijdse beoordeling Sprint 3 D & C 2025-2026",
    "72542": "Untitled",
}


@pytest.fixture(scope="module")
def page():
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    p = browser.new_page()
    p.goto(FIXTURE.as_uri())
    yield p
    browser.close()
    pw.stop()


class TestExtractRubricsFixture:
    def test_finds_all_rubrics(self, page) -> None:
        results = extract_rubrics(page)
        assert len(results) == len(EXPECTED_RUBRICS)

    def test_rubric_ids_match(self, page) -> None:
        results = extract_rubrics(page)
        ids = {r["rubric_id"] for r in results}
        assert ids == set(EXPECTED_RUBRICS.keys())

    def test_rubric_names_match(self, page) -> None:
        results = extract_rubrics(page)
        for r in results:
            expected = EXPECTED_RUBRICS[r["rubric_id"]]
            assert r["name"] == expected, (
                f"ID {r['rubric_id']}: expected {expected!r}, got {r['name']!r}"
            )

    def test_all_have_type(self, page) -> None:
        results = extract_rubrics(page)
        for r in results:
            assert r["type"] in ("Analytic", "Holistic"), (
                f"{r['name']}: unexpected type {r['type']!r}"
            )

    def test_all_have_scoring_method(self, page) -> None:
        results = extract_rubrics(page)
        for r in results:
            assert r["scoring_method"] in (
                "Text Only",
                "Percentages",
                "Points",
                "Custom Points",
            ), f"{r['name']}: unexpected scoring {r['scoring_method']!r}"

    def test_all_have_status(self, page) -> None:
        results = extract_rubrics(page)
        for r in results:
            assert r["status"] in ("Draft", "Published", "Archived"), (
                f"{r['name']}: unexpected status {r['status']!r}"
            )

    def test_returns_dicts_with_expected_keys(self, page) -> None:
        results = extract_rubrics(page)
        for r in results:
            assert "rubric_id" in r
            assert "name" in r
            assert "type" in r
            assert "scoring_method" in r
            assert "status" in r
