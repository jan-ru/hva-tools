"""Shared test fixtures, Hypothesis strategies, and factory helpers."""

from datetime import date
from pathlib import Path

import pytest
from hypothesis import strategies as st
from playwright.sync_api import sync_playwright

from brightspace_extractor.models import (
    AssignmentEntry,
    AssignmentFeedback,
    Criterion,
    GroupFeedback,
    GroupSubmission,
    RubricFeedback,
    Student,
)

# ---------------------------------------------------------------------------
# Reusable constants
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent

ALICE = Student(name="Alice")
BOB = Student(name="Bob")

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def make_criterion(
    name: str = "Quality", score: float = 8.0, feedback: str = "Good"
) -> Criterion:
    return Criterion(name=name, score=score, feedback=feedback)


def make_rubric(*criteria: Criterion) -> RubricFeedback:
    if not criteria:
        criteria = (make_criterion(),)
    return RubricFeedback(criteria=criteria)


# ---------------------------------------------------------------------------
# Hypothesis strategies — model building blocks
# ---------------------------------------------------------------------------

student_st = st.builds(Student, name=st.text(min_size=1, max_size=30))

criterion_st = st.builds(
    Criterion,
    name=st.text(min_size=1, max_size=30),
    score=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    feedback=st.text(max_size=100),
)

rubric_st = st.builds(
    RubricFeedback,
    criteria=st.lists(criterion_st, min_size=1, max_size=5).map(tuple),
)

assignment_entry_st = st.builds(
    AssignmentEntry,
    assignment_name=st.text(min_size=1, max_size=30),
    submission_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2026, 12, 31)),
    rubric=rubric_st,
)

group_feedback_st = st.builds(
    GroupFeedback,
    group_name=st.text(min_size=1, max_size=30),
    students=st.lists(student_st, min_size=1, max_size=4).map(tuple),
    assignments=st.lists(assignment_entry_st, min_size=1, max_size=4).map(tuple),
)

# Use a small fixed pool of group names so groups overlap across assignments
group_name_st = st.sampled_from(["Alpha", "Beta", "Gamma", "Delta"])

group_submission_st = st.builds(
    GroupSubmission,
    group_name=group_name_st,
    students=st.lists(student_st, min_size=1, max_size=4).map(tuple),
    rubric=rubric_st,
    submission_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2026, 12, 31)),
)

assignment_feedback_st = st.builds(
    AssignmentFeedback,
    assignment_name=st.text(min_size=1, max_size=30),
    assignment_id=st.uuids().map(str),
    submissions=st.lists(group_submission_st, min_size=1, max_size=6).map(tuple),
)


# ---------------------------------------------------------------------------
# Shared Playwright fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pw_browser():
    """Module-scoped Playwright browser for fixture tests."""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture(scope="module")
def pw_page(pw_browser, request):
    """Module-scoped Playwright page loaded with the fixture HTML.

    Test modules set ``FIXTURE_NAME`` at module level to specify which
    HTML file to load.  Falls back to requiring the name via a marker.
    """
    fixture_name = getattr(request.module, "FIXTURE_NAME", None)
    if fixture_name is None:
        pytest.skip("No FIXTURE_NAME defined on module")
    page = pw_browser.new_page()
    page.goto((FIXTURES_DIR / fixture_name).as_uri())
    yield page
    page.close()
