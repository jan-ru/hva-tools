"""Integration test for extract_groups using a real Brightspace HTML fixture.

Loads tests/groups-debug.html in a Playwright browser and runs
the scraper against it to validate selectors against actual Brightspace DOM.

Note: the fixture only shows one category (FC2A) since the page requires
JavaScript interaction to switch categories. This test validates the
table scraping for the visible category.
"""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from brightspace_extractor.extraction import _scrape_group_table

FIXTURE = Path(__file__).parent / "groups-debug.html"

# Expected groups in the FC2A category (from the fixture)
EXPECTED_GROUPS = [
    {"group_name": "FC2A - 1", "members": "4/4"},
    {"group_name": "FC2A - 2", "members": "4/4"},
    {"group_name": "FC2A - 3", "members": "4/4"},
    {"group_name": "FC2A - 4", "members": "4/4"},
    {"group_name": "FC2A - 5", "members": "3/4"},
    {"group_name": "FC2A - 6", "members": "4/4"},
    {"group_name": "FC2A - 7", "members": "3/4"},
    {"group_name": "FC2A - 8", "members": "2/4"},
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


class TestScrapeGroupTableFixture:
    """Test _scrape_group_table against real Brightspace HTML."""

    def test_finds_all_groups(self, page) -> None:
        results = _scrape_group_table(page)
        assert len(results) == len(EXPECTED_GROUPS)

    def test_group_names_match(self, page) -> None:
        results = _scrape_group_table(page)
        names = [r["group_name"] for r in results]
        expected_names = [g["group_name"] for g in EXPECTED_GROUPS]
        assert names == expected_names

    def test_member_counts_match(self, page) -> None:
        results = _scrape_group_table(page)
        for result, expected in zip(results, EXPECTED_GROUPS):
            assert result["members"] == expected["members"], (
                f"{result['group_name']}: expected {expected['members']}, "
                f"got {result['members']}"
            )

    def test_returns_list_of_dicts(self, page) -> None:
        results = _scrape_group_table(page)
        for r in results:
            assert "group_name" in r
            assert "members" in r

    def test_fc2a_5_has_3_of_4_members(self, page) -> None:
        results = _scrape_group_table(page)
        fc2a_5 = next(r for r in results if r["group_name"] == "FC2A - 5")
        assert fc2a_5["members"] == "3/4"

    def test_fc2a_8_has_2_of_4_members(self, page) -> None:
        results = _scrape_group_table(page)
        fc2a_8 = next(r for r in results if r["group_name"] == "FC2A - 8")
        assert fc2a_8["members"] == "2/4"
