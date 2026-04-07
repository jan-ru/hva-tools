"""Integration test for extract_quizzes using a real Brightspace HTML fixture."""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from brightspace_extractor.extraction import extract_quizzes

FIXTURE = Path(__file__).parent / "quizzes-debug.html"

EXPECTED_QUIZZES = {
    "72711": "Quiz week 1-2 MAC",
    "72712": "Quiz week 3 MAC",
    "72713": "Quiz week 4 MAC",
    "72714": "Quiz week 5 MAC",
    "72715": "Quiz week 6 MAC",
    "72716": "Quiz week 7A MAC",
    "72717": "Quiz week 7B MAC",
    "72718": "Quiz week 8 MAC",
    "72719": "MAC quiz (herhaling wk 1-wk 7)",
    "72720": "Quiz week 1-2 MAC",
    "72721": "Quiz week 3 MAC",
    "72722": "Quiz week 4 MAC",
    "72723": "Quiz week 5 MAC",
    "72724": "Quiz week 6 MAC",
    "72725": "Quiz week 7A MAC",
    "72726": "Quiz week 7B MAC",
    "72727": "Quiz week 8 MAC",
    "72728": "MAC quiz (herhaling wk 1-wk 7)",
    "72729": "Quiz 0 MIS week 2",
    "72733": "Quiz 2 MIS, week 7, variant 2",
    "72730": "Quiz 1 MIS, week 4, variant 1",
    "72731": "Quiz 1 MIS, week 4",
    "72732": "Quiz 2 MIS, week 7, variant 1",
    "72734": "Quiz 1 MIS, week 4, variant 2",
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


class TestExtractQuizzesFixture:
    def test_finds_all_quizzes(self, page) -> None:
        results = extract_quizzes(page)
        assert len(results) == len(EXPECTED_QUIZZES)

    def test_quiz_ids_match(self, page) -> None:
        results = extract_quizzes(page)
        ids = {r["quiz_id"] for r in results}
        assert ids == set(EXPECTED_QUIZZES.keys())

    def test_quiz_names_match(self, page) -> None:
        results = extract_quizzes(page)
        for r in results:
            expected = EXPECTED_QUIZZES[r["quiz_id"]]
            assert r["name"] == expected, (
                f"ID {r['quiz_id']}: expected {expected!r}, got {r['name']!r}"
            )

    def test_mac_quiz_present(self, page) -> None:
        results = extract_quizzes(page)
        names = {r["name"] for r in results}
        assert "Quiz week 1-2 MAC" in names

    def test_returns_dicts_with_expected_keys(self, page) -> None:
        results = extract_quizzes(page)
        for r in results:
            assert "quiz_id" in r
            assert "name" in r
