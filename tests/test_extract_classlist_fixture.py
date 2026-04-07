"""Integration test for extract_classlist using a real Brightspace HTML fixture.

Loads tests/classlist-debug.html in a Playwright browser and runs
the scraper against it to validate selectors against actual Brightspace DOM.
"""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from brightspace_extractor.extraction import extract_classlist

FIXTURE = Path(__file__).parent / "classlist-debug.html"

# Total users shown on the page (from "Total Users: 37")
EXPECTED_TOTAL = 37

# A few known students to spot-check
KNOWN_STUDENTS = [
    {"name": "Anwar Laroub", "org_defined_id": "500908250", "role": "Student"},
    {"name": "Bas Koot", "org_defined_id": "500978594", "role": "Student"},
    {"name": "Carmen Jordaan", "org_defined_id": "500948231", "role": "Student"},
]

# Known lecturers
KNOWN_LECTURERS = [
    {
        "name": "Diederik Ogilvie",
        "org_defined_id": "ogide",
        "role": "Designing Lecturer",
    },
    {
        "name": "Jan-Ru Muller",
        "org_defined_id": "jrmulle",
        "role": "Designing Lecturer",
    },
    {
        "name": "Joyce van Weering",
        "org_defined_id": "jweerin",
        "role": "Designing Lecturer",
    },
    {"name": "Paul te Riele", "org_defined_id": "riepc", "role": "Designing Lecturer"},
]


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


class TestExtractClasslistFixture:
    """Test extract_classlist against real Brightspace HTML."""

    def test_finds_correct_total(self, page) -> None:
        results = extract_classlist(page)
        assert len(results) == EXPECTED_TOTAL

    def test_returns_list_of_dicts_with_expected_keys(self, page) -> None:
        results = extract_classlist(page)
        for r in results:
            assert "name" in r
            assert "org_defined_id" in r
            assert "role" in r

    def test_known_students_present(self, page) -> None:
        results = extract_classlist(page)
        names = {r["name"] for r in results}
        for student in KNOWN_STUDENTS:
            assert student["name"] in names

    def test_known_student_org_ids(self, page) -> None:
        results = extract_classlist(page)
        by_name = {r["name"]: r for r in results}
        for student in KNOWN_STUDENTS:
            result = by_name[student["name"]]
            assert result["org_defined_id"] == student["org_defined_id"]
            assert result["role"] == student["role"]

    def test_known_lecturers_present(self, page) -> None:
        results = extract_classlist(page)
        by_name = {r["name"]: r for r in results}
        for lecturer in KNOWN_LECTURERS:
            assert lecturer["name"] in by_name
            result = by_name[lecturer["name"]]
            assert result["org_defined_id"] == lecturer["org_defined_id"]
            assert result["role"] == "Designing Lecturer"

    def test_all_roles_are_student_or_lecturer(self, page) -> None:
        results = extract_classlist(page)
        roles = {r["role"] for r in results}
        assert roles <= {"Student", "Designing Lecturer", "-"}

    def test_no_empty_names(self, page) -> None:
        results = extract_classlist(page)
        for r in results:
            assert r["name"].strip() != ""
