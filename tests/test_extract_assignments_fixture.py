"""Integration test for extract_assignments using a real Brightspace HTML fixture.

Loads tests/assignments-debug.html in a Playwright browser and runs
the scraper against it to validate selectors against actual Brightspace DOM.
"""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from brightspace_extractor.extraction import extract_assignments

FIXTURE = Path(__file__).parent / "assignments-debug.html"

# Expected assignments extracted from the fixture HTML (db=ID → name)
EXPECTED_ASSIGNMENTS = {
    "336740": "Proces: Verslag en gesprek",
    "336761": "Beroepsproduct Management Accounting",
    "336741": "Data & Control Sprint 1 FC2A",
    "336753": "Data & Control Sprint 1 FC2C",
    "336743": "Data & Control Sprint 2 FC2A",
    "336748": "Data & Control Sprint 2 FC2C",
    "336744": "Data & Control Sprint 3 FC2A",
    "336749": "Data & Control Sprint 3 FC2C",
    "336727": "Groepscontract FC2A",
    "336729": "Groepscontract FC2C",
    "336731": "FC2A Feedbackformulier sprint 1",
    "336734": "FC2C Feedbackformulier sprint 1",
    "336735": "formulier en opdracht Individueel slb gesprek",
    "336754": "Goodhabitz persoonlijk leiderschap",
    "336736": "Groepsproces",
    "336737": "FC2A Feedbackformulier sprint 2",
    "336756": "FC2C Feedbackformulier sprint 2",
    "336730": "FC2A Feedbackformulier sprint 3",
    "336757": "FC2C Feedbackformulier sprint 3",
    "336747": "Onderzoek bij Data & Control cursus Zoeklicht Basis en Zoeklicht Gevorderd",
    "336762": "FC2A Presentatie onderzoekend vermogen bij les 3 onderzoekend vermogen",
    "336764": "FC2C Presentatie onderzoekend vermogen bij les 3 onderzoekend vermogen",
    "336750": "Beoordeling beroepsproduct FC2A",
    "336752": "Beoordeling beroepsproduct FC2C",
    "336739": "Procesverslag Data & Control",
    "336755": "Herkansing beroepsproduct Data & Control (Individueel)",
    "336758": "Beroepsproduct Data & Control (individueel)",
    "336760": "Power BI basis",
}


@pytest.fixture(scope="module")
def page():
    """Launch a headless browser and yield a Page with the fixture loaded."""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    p = browser.new_page()
    p.goto(FIXTURE.as_uri())
    yield p
    browser.close()
    pw.stop()


class TestExtractAssignmentsFixture:
    """Test extract_assignments against real Brightspace HTML."""

    def test_finds_all_assignments(self, page) -> None:
        results = extract_assignments(page)
        assert len(results) == len(EXPECTED_ASSIGNMENTS)

    def test_assignment_ids_match(self, page) -> None:
        results = extract_assignments(page)
        ids = {r["assignment_id"] for r in results}
        assert ids == set(EXPECTED_ASSIGNMENTS.keys())

    def test_assignment_names_match(self, page) -> None:
        results = extract_assignments(page)
        for r in results:
            expected_name = EXPECTED_ASSIGNMENTS[r["assignment_id"]]
            assert r["name"] == expected_name, (
                f"ID {r['assignment_id']}: expected {expected_name!r}, got {r['name']!r}"
            )

    def test_power_bi_basis_present(self, page) -> None:
        results = extract_assignments(page)
        names = {r["name"] for r in results}
        assert "Power BI basis" in names

    def test_power_bi_basis_id(self, page) -> None:
        results = extract_assignments(page)
        pbi = next(r for r in results if r["name"] == "Power BI basis")
        assert pbi["assignment_id"] == "336760"

    def test_returns_list_of_dicts(self, page) -> None:
        results = extract_assignments(page)
        for r in results:
            assert "assignment_id" in r
            assert "name" in r
            assert isinstance(r["assignment_id"], str)
            assert isinstance(r["name"], str)
