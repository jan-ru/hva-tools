"""Integration test for extract_groups using a real Brightspace HTML fixture.

Loads tests/groups-debug.html in a Playwright browser and runs
the scraper against it to validate selectors against actual Brightspace DOM.

Note: the fixture only shows one category (FC2A) since the page requires
JavaScript interaction to switch categories. This test validates the
table scraping for the visible category.
"""

from brightspace_extractor.extraction import _scrape_group_table
from tests.expected_data import EXPECTED_GROUPS

FIXTURE_NAME = "groups-debug.html"


class TestScrapeGroupTableFixture:
    """Test _scrape_group_table against real Brightspace HTML."""

    def test_finds_all_groups(self, pw_page) -> None:
        results = _scrape_group_table(pw_page)
        assert len(results) == len(EXPECTED_GROUPS)

    def test_group_names_match(self, pw_page) -> None:
        results = _scrape_group_table(pw_page)
        names = [r["group_name"] for r in results]
        expected_names = [g["group_name"] for g in EXPECTED_GROUPS]
        assert names == expected_names

    def test_member_counts_match(self, pw_page) -> None:
        results = _scrape_group_table(pw_page)
        for result, expected in zip(results, EXPECTED_GROUPS):
            assert result["members"] == expected["members"], (
                f"{result['group_name']}: expected {expected['members']}, "
                f"got {result['members']}"
            )

    def test_returns_list_of_dicts(self, pw_page) -> None:
        results = _scrape_group_table(pw_page)
        for r in results:
            assert "group_name" in r
            assert "members" in r

    def test_fc2a_5_has_3_of_4_members(self, pw_page) -> None:
        results = _scrape_group_table(pw_page)
        fc2a_5 = next(r for r in results if r["group_name"] == "FC2A - 5")
        assert fc2a_5["members"] == "3/4"

    def test_fc2a_8_has_2_of_4_members(self, pw_page) -> None:
        results = _scrape_group_table(pw_page)
        fc2a_8 = next(r for r in results if r["group_name"] == "FC2A - 8")
        assert fc2a_8["members"] == "2/4"
