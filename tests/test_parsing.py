"""Unit tests for raw dict → model parsing."""

from datetime import date

import pytest

from brightspace_extractor.parsing import parse_all_submissions, parse_group_submission


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_raw(
    *, group_name="Group A", students=None, criteria=None, submission_date="2025-03-15"
):
    """Return a minimal valid raw dict, with optional overrides."""
    return {
        "group_name": group_name,
        "students": students or ["Alice", "Bob"],
        "criteria": criteria or [{"name": "Clarity", "score": 8.0, "feedback": "Good"}],
        "submission_date": submission_date,
    }


# ---------------------------------------------------------------------------
# parse_group_submission – valid inputs
# ---------------------------------------------------------------------------


class TestParseGroupSubmissionValid:
    def test_basic_valid_dict(self):
        raw = _valid_raw()
        result = parse_group_submission(raw)

        assert result.group_name == "Group A"
        assert len(result.students) == 2
        assert result.students[0].name == "Alice"
        assert result.rubric.criteria[0].name == "Clarity"
        assert result.rubric.criteria[0].score == 8.0
        assert result.submission_date == date(2025, 3, 15)

    def test_date_object_accepted(self):
        raw = _valid_raw(submission_date=date(2025, 1, 1))
        result = parse_group_submission(raw)
        assert result.submission_date == date(2025, 1, 1)

    def test_multiple_criteria(self):
        criteria = [
            {"name": "Clarity", "score": 8.0, "feedback": "Good"},
            {"name": "Depth", "score": 6.5, "feedback": ""},
        ]
        result = parse_group_submission(_valid_raw(criteria=criteria))
        assert len(result.rubric.criteria) == 2

    def test_missing_feedback_defaults_to_empty(self):
        criteria = [{"name": "Clarity", "score": 8.0}]
        result = parse_group_submission(_valid_raw(criteria=criteria))
        assert result.rubric.criteria[0].feedback == ""

    def test_single_student(self):
        result = parse_group_submission(_valid_raw(students=["Solo"]))
        assert len(result.students) == 1
        assert result.students[0].name == "Solo"


# ---------------------------------------------------------------------------
# parse_group_submission – malformed inputs
# ---------------------------------------------------------------------------


class TestParseGroupSubmissionMalformed:
    def test_missing_group_name(self):
        raw = _valid_raw()
        del raw["group_name"]
        with pytest.raises(ValueError, match="Missing required field"):
            parse_group_submission(raw)

    def test_missing_students(self):
        raw = _valid_raw()
        del raw["students"]
        with pytest.raises(ValueError, match="Missing required field"):
            parse_group_submission(raw)

    def test_missing_criteria(self):
        raw = _valid_raw()
        del raw["criteria"]
        with pytest.raises(ValueError, match="Missing required field"):
            parse_group_submission(raw)

    def test_missing_submission_date(self):
        raw = _valid_raw()
        del raw["submission_date"]
        with pytest.raises(ValueError, match="Missing required field"):
            parse_group_submission(raw)

    def test_bad_date_string(self):
        with pytest.raises(ValueError):
            parse_group_submission(_valid_raw(submission_date="not-a-date"))

    def test_criteria_missing_name(self):
        criteria = [{"score": 5.0, "feedback": "ok"}]
        with pytest.raises(ValueError):
            parse_group_submission(_valid_raw(criteria=criteria))

    def test_criteria_missing_score(self):
        criteria = [{"name": "Clarity", "feedback": "ok"}]
        with pytest.raises(ValueError):
            parse_group_submission(_valid_raw(criteria=criteria))

    def test_students_not_iterable(self):
        with pytest.raises(ValueError):
            parse_group_submission(_valid_raw(students=42))

    def test_criteria_not_iterable(self):
        with pytest.raises(ValueError):
            parse_group_submission(_valid_raw(criteria="bad"))


# ---------------------------------------------------------------------------
# parse_all_submissions
# ---------------------------------------------------------------------------


class TestParseAllSubmissions:
    def test_all_valid(self):
        raws = [_valid_raw(group_name="G1"), _valid_raw(group_name="G2")]
        result = parse_all_submissions(raws, "HW1", "hw-1")

        assert len(result) == 1
        af = result[0]
        assert af.assignment_name == "HW1"
        assert af.assignment_id == "hw-1"
        assert len(af.submissions) == 2

    def test_skips_malformed_entries(self):
        good = _valid_raw(group_name="Good")
        bad = {"group_name": "Bad"}  # missing required fields
        result = parse_all_submissions([good, bad], "HW1", "hw-1")

        assert len(result) == 1
        assert len(result[0].submissions) == 1
        assert result[0].submissions[0].group_name == "Good"

    def test_all_malformed_returns_empty(self):
        bad1 = {"group_name": "A"}
        bad2 = {"students": ["x"]}
        result = parse_all_submissions([bad1, bad2], "HW1", "hw-1")
        assert result == []

    def test_empty_input_returns_empty(self):
        assert parse_all_submissions([], "HW1", "hw-1") == []
