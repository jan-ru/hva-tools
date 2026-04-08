"""Integration test for extract_classlist using a real Brightspace HTML fixture.

Loads tests/classlist-debug.html in a Playwright browser and runs
the scraper against it to validate selectors against actual Brightspace DOM.
"""

from brightspace_extractor.extraction import extract_classlist
from tests.expected_data import (
    EXPECTED_CLASSLIST_TOTAL,
    KNOWN_LECTURERS,
    KNOWN_STUDENTS,
)

FIXTURE_NAME = "classlist-debug.html"


class TestExtractClasslistFixture:
    """Test extract_classlist against real Brightspace HTML."""

    def test_finds_correct_total(self, pw_page) -> None:
        results = extract_classlist(pw_page)
        assert len(results) == EXPECTED_CLASSLIST_TOTAL

    def test_returns_list_of_dicts_with_expected_keys(self, pw_page) -> None:
        results = extract_classlist(pw_page)
        for r in results:
            assert "name" in r
            assert "org_defined_id" in r
            assert "role" in r

    def test_known_students_present(self, pw_page) -> None:
        results = extract_classlist(pw_page)
        names = {r["name"] for r in results}
        for student in KNOWN_STUDENTS:
            assert student["name"] in names

    def test_known_student_org_ids(self, pw_page) -> None:
        results = extract_classlist(pw_page)
        by_name = {r["name"]: r for r in results}
        for student in KNOWN_STUDENTS:
            result = by_name[student["name"]]
            assert result["org_defined_id"] == student["org_defined_id"]
            assert result["role"] == student["role"]

    def test_known_lecturers_present(self, pw_page) -> None:
        results = extract_classlist(pw_page)
        by_name = {r["name"]: r for r in results}
        for lecturer in KNOWN_LECTURERS:
            assert lecturer["name"] in by_name
            result = by_name[lecturer["name"]]
            assert result["org_defined_id"] == lecturer["org_defined_id"]
            assert result["role"] == "Designing Lecturer"

    def test_all_roles_are_student_or_lecturer(self, pw_page) -> None:
        results = extract_classlist(pw_page)
        roles = {r["role"] for r in results}
        assert roles <= {"Student", "Designing Lecturer", "-"}

    def test_no_empty_names(self, pw_page) -> None:
        results = extract_classlist(pw_page)
        for r in results:
            assert r["name"].strip() != ""
