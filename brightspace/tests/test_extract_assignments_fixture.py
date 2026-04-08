"""Integration test for extract_assignments using a real Brightspace HTML fixture.

Loads tests/assignments-debug.html in a Playwright browser and runs
the scraper against it to validate selectors against actual Brightspace DOM.
"""

from brightspace_extractor.extraction import extract_assignments
from tests.expected_data import EXPECTED_ASSIGNMENTS

FIXTURE_NAME = "assignments-debug.html"


class TestExtractAssignmentsFixture:
    """Test extract_assignments against real Brightspace HTML."""

    def test_finds_all_assignments(self, pw_page) -> None:
        results = extract_assignments(pw_page)
        assert len(results) == len(EXPECTED_ASSIGNMENTS)

    def test_assignment_ids_match(self, pw_page) -> None:
        results = extract_assignments(pw_page)
        ids = {r["assignment_id"] for r in results}
        assert ids == set(EXPECTED_ASSIGNMENTS.keys())

    def test_assignment_names_match(self, pw_page) -> None:
        results = extract_assignments(pw_page)
        for r in results:
            expected_name = EXPECTED_ASSIGNMENTS[r["assignment_id"]]
            assert r["name"] == expected_name, (
                f"ID {r['assignment_id']}: expected {expected_name!r}, got {r['name']!r}"
            )

    def test_power_bi_basis_present(self, pw_page) -> None:
        results = extract_assignments(pw_page)
        names = {r["name"] for r in results}
        assert "Power BI basis" in names

    def test_power_bi_basis_id(self, pw_page) -> None:
        results = extract_assignments(pw_page)
        pbi = next(r for r in results if r["name"] == "Power BI basis")
        assert pbi["assignment_id"] == "336760"

    def test_returns_list_of_dicts(self, pw_page) -> None:
        results = extract_assignments(pw_page)
        for r in results:
            assert "assignment_id" in r
            assert "name" in r
            assert isinstance(r["assignment_id"], str)
            assert isinstance(r["name"], str)
