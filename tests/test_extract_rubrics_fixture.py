"""Integration test for extract_rubrics using a real Brightspace HTML fixture."""

from brightspace_extractor.extraction import extract_rubrics
from tests.expected_data import EXPECTED_RUBRICS

FIXTURE_NAME = "rubrics-debug.html"


class TestExtractRubricsFixture:
    def test_finds_all_rubrics(self, pw_page) -> None:
        results = extract_rubrics(pw_page)
        assert len(results) == len(EXPECTED_RUBRICS)

    def test_rubric_ids_match(self, pw_page) -> None:
        results = extract_rubrics(pw_page)
        ids = {r["rubric_id"] for r in results}
        assert ids == set(EXPECTED_RUBRICS.keys())

    def test_rubric_names_match(self, pw_page) -> None:
        results = extract_rubrics(pw_page)
        for r in results:
            expected = EXPECTED_RUBRICS[r["rubric_id"]]
            assert r["name"] == expected, (
                f"ID {r['rubric_id']}: expected {expected!r}, got {r['name']!r}"
            )

    def test_all_have_type(self, pw_page) -> None:
        results = extract_rubrics(pw_page)
        for r in results:
            assert r["type"] in ("Analytic", "Holistic"), (
                f"{r['name']}: unexpected type {r['type']!r}"
            )

    def test_all_have_scoring_method(self, pw_page) -> None:
        results = extract_rubrics(pw_page)
        for r in results:
            assert r["scoring_method"] in (
                "Text Only",
                "Percentages",
                "Points",
                "Custom Points",
            ), f"{r['name']}: unexpected scoring {r['scoring_method']!r}"

    def test_all_have_status(self, pw_page) -> None:
        results = extract_rubrics(pw_page)
        for r in results:
            assert r["status"] in ("Draft", "Published", "Archived"), (
                f"{r['name']}: unexpected status {r['status']!r}"
            )

    def test_returns_dicts_with_expected_keys(self, pw_page) -> None:
        results = extract_rubrics(pw_page)
        for r in results:
            assert "rubric_id" in r
            assert "name" in r
            assert "type" in r
            assert "scoring_method" in r
            assert "status" in r
