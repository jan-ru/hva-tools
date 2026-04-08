"""Integration test for extract_quizzes using a real Brightspace HTML fixture."""

from brightspace_extractor.extraction import extract_quizzes
from tests.expected_data import EXPECTED_QUIZZES

FIXTURE_NAME = "quizzes-debug.html"


class TestExtractQuizzesFixture:
    def test_finds_all_quizzes(self, pw_page) -> None:
        results = extract_quizzes(pw_page)
        assert len(results) == len(EXPECTED_QUIZZES)

    def test_quiz_ids_match(self, pw_page) -> None:
        results = extract_quizzes(pw_page)
        ids = {r["quiz_id"] for r in results}
        assert ids == set(EXPECTED_QUIZZES.keys())

    def test_quiz_names_match(self, pw_page) -> None:
        results = extract_quizzes(pw_page)
        for r in results:
            expected = EXPECTED_QUIZZES[r["quiz_id"]]
            assert r["name"] == expected, (
                f"ID {r['quiz_id']}: expected {expected!r}, got {r['name']!r}"
            )

    def test_mac_quiz_present(self, pw_page) -> None:
        results = extract_quizzes(pw_page)
        names = {r["name"] for r in results}
        assert "Quiz week 1-2 MAC" in names

    def test_returns_dicts_with_expected_keys(self, pw_page) -> None:
        results = extract_quizzes(pw_page)
        for r in results:
            assert "quiz_id" in r
            assert "name" in r
