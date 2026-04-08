"""Validate ExtractionAdapter against all HTML fixture files.

Each test class loads a fixture with the adapter (no Playwright) and verifies
the extraction output matches the same expectations as the Playwright-based tests.
"""

from pathlib import Path

import pytest

from brightspace_extractor.adapter import ExtractionAdapter
from brightspace_extractor.extraction import (
    _scrape_group_table,
    extract_assignments,
    extract_classlist,
    extract_quizzes,
    extract_rubrics,
)
from tests.expected_data import (
    EXPECTED_ASSIGNMENTS,
    EXPECTED_CLASSLIST_TOTAL,
    EXPECTED_GROUPS,
    EXPECTED_QUIZZES,
    EXPECTED_RUBRICS,
    KNOWN_LECTURERS,
    KNOWN_STUDENTS,
)

FIXTURES = Path(__file__).parent


def _load(name: str) -> ExtractionAdapter:
    return ExtractionAdapter((FIXTURES / name).read_text(encoding="utf-8"))


# ── Assignments ──────────────────────────────────────────────────────────────


class TestAdapterAssignments:
    @pytest.fixture(scope="class")
    def adapter(self):
        return _load("assignments-debug.html")

    def test_finds_all_assignments(self, adapter) -> None:
        results = extract_assignments(adapter)
        assert len(results) == len(EXPECTED_ASSIGNMENTS)

    def test_assignment_ids_match(self, adapter) -> None:
        results = extract_assignments(adapter)
        ids = {r["assignment_id"] for r in results}
        assert ids == set(EXPECTED_ASSIGNMENTS.keys())

    def test_assignment_names_match(self, adapter) -> None:
        results = extract_assignments(adapter)
        for r in results:
            expected = EXPECTED_ASSIGNMENTS[r["assignment_id"]]
            assert r["name"] == expected


# ── Classlist ────────────────────────────────────────────────────────────────


class TestAdapterClasslist:
    @pytest.fixture(scope="class")
    def adapter(self):
        return _load("classlist-debug.html")

    def test_finds_correct_total(self, adapter) -> None:
        results = extract_classlist(adapter)
        assert len(results) == EXPECTED_CLASSLIST_TOTAL

    def test_known_students_present(self, adapter) -> None:
        results = extract_classlist(adapter)
        by_name = {r["name"]: r for r in results}
        for student in KNOWN_STUDENTS:
            assert student["name"] in by_name
            r = by_name[student["name"]]
            assert r["org_defined_id"] == student["org_defined_id"]
            assert r["role"] == student["role"]

    def test_known_lecturers_present(self, adapter) -> None:
        results = extract_classlist(adapter)
        by_name = {r["name"]: r for r in results}
        for lecturer in KNOWN_LECTURERS:
            assert lecturer["name"] in by_name
            r = by_name[lecturer["name"]]
            assert r["org_defined_id"] == lecturer["org_defined_id"]
            assert r["role"] == "Designing Lecturer"

    def test_no_empty_names(self, adapter) -> None:
        results = extract_classlist(adapter)
        for r in results:
            assert r["name"].strip() != ""


# ── Groups ───────────────────────────────────────────────────────────────────


class TestAdapterGroups:
    @pytest.fixture(scope="class")
    def adapter(self):
        return _load("groups-debug.html")

    def test_finds_all_groups(self, adapter) -> None:
        results = _scrape_group_table(adapter)
        assert len(results) == len(EXPECTED_GROUPS)

    def test_group_names_match(self, adapter) -> None:
        results = _scrape_group_table(adapter)
        names = [r["group_name"] for r in results]
        expected_names = [g["group_name"] for g in EXPECTED_GROUPS]
        assert names == expected_names

    def test_member_counts_match(self, adapter) -> None:
        results = _scrape_group_table(adapter)
        for result, expected in zip(results, EXPECTED_GROUPS):
            assert result["members"] == expected["members"]


# ── Quizzes ──────────────────────────────────────────────────────────────────


class TestAdapterQuizzes:
    @pytest.fixture(scope="class")
    def adapter(self):
        return _load("quizzes-debug.html")

    def test_finds_all_quizzes(self, adapter) -> None:
        results = extract_quizzes(adapter)
        assert len(results) == len(EXPECTED_QUIZZES)

    def test_quiz_ids_match(self, adapter) -> None:
        results = extract_quizzes(adapter)
        ids = {r["quiz_id"] for r in results}
        assert ids == set(EXPECTED_QUIZZES.keys())

    def test_quiz_names_match(self, adapter) -> None:
        results = extract_quizzes(adapter)
        for r in results:
            expected = EXPECTED_QUIZZES[r["quiz_id"]]
            assert r["name"] == expected


# ── Rubrics ──────────────────────────────────────────────────────────────────


class TestAdapterRubrics:
    @pytest.fixture(scope="class")
    def adapter(self):
        return _load("rubrics-debug.html")

    def test_finds_all_rubrics(self, adapter) -> None:
        results = extract_rubrics(adapter)
        assert len(results) == len(EXPECTED_RUBRICS)

    def test_rubric_ids_match(self, adapter) -> None:
        results = extract_rubrics(adapter)
        ids = {r["rubric_id"] for r in results}
        assert ids == set(EXPECTED_RUBRICS.keys())

    def test_rubric_names_match(self, adapter) -> None:
        results = extract_rubrics(adapter)
        for r in results:
            expected = EXPECTED_RUBRICS[r["rubric_id"]]
            assert r["name"] == expected

    def test_all_have_type(self, adapter) -> None:
        results = extract_rubrics(adapter)
        for r in results:
            assert r["type"] in ("Analytic", "Holistic")

    def test_all_have_scoring_method(self, adapter) -> None:
        results = extract_rubrics(adapter)
        for r in results:
            assert r["scoring_method"] in (
                "Text Only",
                "Percentages",
                "Points",
                "Custom Points",
            )

    def test_all_have_status(self, adapter) -> None:
        results = extract_rubrics(adapter)
        for r in results:
            assert r["status"] in ("Draft", "Published", "Archived")
