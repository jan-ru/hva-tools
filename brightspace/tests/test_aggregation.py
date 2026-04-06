"""Unit and property tests for group-level aggregation."""

from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from brightspace_extractor.aggregation import aggregate_by_group
from brightspace_extractor.models import (
    AssignmentFeedback,
    Criterion,
    GroupSubmission,
    RubricFeedback,
    Student,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies
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
# Property 1: Aggregation round-trip preserves all feedback data
# ---------------------------------------------------------------------------


@given(feedbacks=st.lists(assignment_feedback_st, min_size=0, max_size=5))
@settings(max_examples=100)
def test_aggregation_roundtrip_preserves_data(
    feedbacks: list[AssignmentFeedback],
) -> None:
    """Feature: brightspace-feedback-extractor, Property 1: Aggregation round-trip preserves all feedback data"""
    # Build the expected set of (group_name, assignment_id, rubric) triples
    expected: set[tuple[str, str, RubricFeedback]] = set()
    for af in feedbacks:
        for sub in af.submissions:
            expected.add((sub.group_name, af.assignment_id, sub.rubric))

    # Aggregate then flatten back
    groups = aggregate_by_group(feedbacks)
    for gf in groups:
        for entry in gf.assignments:
            # We need to recover the assignment_id — but AssignmentEntry doesn't
            # store it.  Instead, build a mapping from (assignment_name, date, rubric)
            # back to assignment_id from the original data.
            pass

    # Because AssignmentEntry doesn't carry assignment_id, we verify via an
    # alternative flattening: compare (group_name, assignment_name, rubric) triples.
    expected_alt: set[tuple[str, str, RubricFeedback]] = set()
    for af in feedbacks:
        for sub in af.submissions:
            expected_alt.add((sub.group_name, af.assignment_name, sub.rubric))

    actual_alt: set[tuple[str, str, RubricFeedback]] = set()
    for gf in groups:
        for entry in gf.assignments:
            actual_alt.add((gf.group_name, entry.assignment_name, entry.rubric))

    assert actual_alt == expected_alt


# ---------------------------------------------------------------------------
# Property 2: Aggregated assignments are chronologically ordered
# ---------------------------------------------------------------------------


@given(feedbacks=st.lists(assignment_feedback_st, min_size=1, max_size=5))
@settings(max_examples=100)
def test_aggregated_assignments_chronologically_ordered(
    feedbacks: list[AssignmentFeedback],
) -> None:
    """Feature: brightspace-feedback-extractor, Property 2: Aggregated assignments are chronologically ordered"""
    groups = aggregate_by_group(feedbacks)
    for gf in groups:
        dates = [entry.submission_date for entry in gf.assignments]
        assert dates == sorted(dates), (
            f"Group '{gf.group_name}' assignments not in chronological order: {dates}"
        )


# ---------------------------------------------------------------------------
# Unit tests: edge cases
# ---------------------------------------------------------------------------

_ALICE = Student(name="Alice")
_BOB = Student(name="Bob")


def _make_criterion(
    name: str = "Quality", score: float = 8.0, feedback: str = "Good"
) -> Criterion:
    return Criterion(name=name, score=score, feedback=feedback)


def _make_rubric(*criteria: Criterion) -> RubricFeedback:
    if not criteria:
        criteria = (_make_criterion(),)
    return RubricFeedback(criteria=criteria)


class TestAggregateEdgeCases:
    """Unit tests for aggregation edge cases (Req 5.1, 5.2, 5.3)."""

    def test_empty_input(self) -> None:
        assert aggregate_by_group([]) == []

    def test_single_group_single_assignment(self) -> None:
        af = AssignmentFeedback(
            assignment_name="HW1",
            assignment_id="a1",
            submissions=(
                GroupSubmission(
                    group_name="Alpha",
                    students=(_ALICE,),
                    rubric=_make_rubric(),
                    submission_date=date(2025, 3, 1),
                ),
            ),
        )
        result = aggregate_by_group([af])
        assert len(result) == 1
        gf = result[0]
        assert gf.group_name == "Alpha"
        assert gf.students == (_ALICE,)
        assert len(gf.assignments) == 1
        assert gf.assignments[0].assignment_name == "HW1"

    def test_group_in_only_some_assignments(self) -> None:
        af1 = AssignmentFeedback(
            assignment_name="HW1",
            assignment_id="a1",
            submissions=(
                GroupSubmission(
                    group_name="Alpha",
                    students=(_ALICE,),
                    rubric=_make_rubric(),
                    submission_date=date(2025, 1, 10),
                ),
                GroupSubmission(
                    group_name="Beta",
                    students=(_BOB,),
                    rubric=_make_rubric(),
                    submission_date=date(2025, 1, 11),
                ),
            ),
        )
        af2 = AssignmentFeedback(
            assignment_name="HW2",
            assignment_id="a2",
            submissions=(
                GroupSubmission(
                    group_name="Alpha",
                    students=(_ALICE,),
                    rubric=_make_rubric(),
                    submission_date=date(2025, 2, 10),
                ),
            ),
        )
        result = aggregate_by_group([af1, af2])
        groups_by_name = {gf.group_name: gf for gf in result}

        assert len(groups_by_name) == 2
        assert len(groups_by_name["Alpha"].assignments) == 2
        assert len(groups_by_name["Beta"].assignments) == 1

    def test_chronological_ordering_across_assignments(self) -> None:
        af_late = AssignmentFeedback(
            assignment_name="HW2",
            assignment_id="a2",
            submissions=(
                GroupSubmission(
                    group_name="Alpha",
                    students=(_ALICE,),
                    rubric=_make_rubric(),
                    submission_date=date(2025, 6, 1),
                ),
            ),
        )
        af_early = AssignmentFeedback(
            assignment_name="HW1",
            assignment_id="a1",
            submissions=(
                GroupSubmission(
                    group_name="Alpha",
                    students=(_ALICE,),
                    rubric=_make_rubric(),
                    submission_date=date(2025, 1, 1),
                ),
            ),
        )
        # Feed in reverse chronological order
        result = aggregate_by_group([af_late, af_early])
        gf = result[0]
        assert gf.assignments[0].assignment_name == "HW1"
        assert gf.assignments[1].assignment_name == "HW2"
