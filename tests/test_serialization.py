"""Unit and property tests for markdown rendering."""

from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from brightspace_extractor.models import (
    AssignmentEntry,
    Criterion,
    GroupFeedback,
    RubricFeedback,
    Student,
)
from brightspace_extractor.serialization import (
    render_group_markdown,
    write_feedback_files,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies (reused from test_aggregation pattern)
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


# ---------------------------------------------------------------------------
# Property 3: Markdown output contains all required feedback information
# ---------------------------------------------------------------------------


@given(gf=group_feedback_st)
@settings(max_examples=100)
def test_markdown_contains_all_required_info(gf: GroupFeedback) -> None:
    """Feature: brightspace-feedback-extractor, Property 3: Markdown output contains all required feedback information"""
    md = render_group_markdown(gf)

    # Group name present
    assert gf.group_name in md

    # Every student name present
    for student in gf.students:
        assert student.name in md

    # Every assignment's info present
    for entry in gf.assignments:
        assert entry.assignment_name in md
        assert entry.submission_date.isoformat() in md

        # Every criterion's data present
        for criterion in entry.rubric.criteria:
            assert criterion.name.replace("|", "\\|") in md
            assert str(criterion.score) in md
            assert criterion.feedback.replace("|", "\\|") in md


# ---------------------------------------------------------------------------
# Unit tests for serialization
# ---------------------------------------------------------------------------

_ALICE = Student(name="Alice")
_BOB = Student(name="Bob")


def _criterion(
    name: str = "Quality", score: float = 8.0, feedback: str = "Good"
) -> Criterion:
    return Criterion(name=name, score=score, feedback=feedback)


def _rubric(*criteria: Criterion) -> RubricFeedback:
    if not criteria:
        criteria = (_criterion(),)
    return RubricFeedback(criteria=criteria)


def _group_feedback() -> GroupFeedback:
    return GroupFeedback(
        group_name="Team Alpha",
        students=(_ALICE, _BOB),
        assignments=(
            AssignmentEntry(
                assignment_name="HW1",
                submission_date=date(2025, 3, 1),
                rubric=_rubric(
                    _criterion("Clarity", 9.0, "Very clear"),
                    _criterion("Depth", 7.5, "Could go deeper"),
                ),
            ),
        ),
    )


class TestRenderGroupMarkdown:
    """Unit tests for render_group_markdown (Req 6.1–6.4)."""

    def test_known_output(self) -> None:
        gf = _group_feedback()
        md = render_group_markdown(gf)

        expected = (
            "# Team Alpha\n"
            "\n"
            "**Students:** Alice, Bob\n"
            "\n"
            "## HW1\n"
            "\n"
            "**Date:** 2025-03-01\n"
            "\n"
            "| Criterion | Score | Feedback |\n"
            "|---|---|---|\n"
            "| Clarity | 9.0 | Very clear |\n"
            "| Depth | 7.5 | Could go deeper |\n"
        )
        assert md == expected

    def test_contains_group_name_heading(self) -> None:
        gf = _group_feedback()
        md = render_group_markdown(gf)
        assert md.startswith("# Team Alpha\n")

    def test_contains_student_names(self) -> None:
        gf = _group_feedback()
        md = render_group_markdown(gf)
        assert "Alice" in md
        assert "Bob" in md

    def test_contains_assignment_section(self) -> None:
        gf = _group_feedback()
        md = render_group_markdown(gf)
        assert "## HW1" in md
        assert "2025-03-01" in md

    def test_contains_criteria_table(self) -> None:
        gf = _group_feedback()
        md = render_group_markdown(gf)
        assert "| Clarity | 9.0 | Very clear |" in md
        assert "| Depth | 7.5 | Could go deeper |" in md

    def test_multiple_assignments(self) -> None:
        gf = GroupFeedback(
            group_name="Team Beta",
            students=(_ALICE,),
            assignments=(
                AssignmentEntry(
                    assignment_name="HW1",
                    submission_date=date(2025, 1, 15),
                    rubric=_rubric(_criterion("A", 5.0, "ok")),
                ),
                AssignmentEntry(
                    assignment_name="HW2",
                    submission_date=date(2025, 2, 20),
                    rubric=_rubric(_criterion("B", 10.0, "great")),
                ),
            ),
        )
        md = render_group_markdown(gf)
        assert "## HW1" in md
        assert "## HW2" in md
        assert "2025-01-15" in md
        assert "2025-02-20" in md


class TestWriteFeedbackFiles:
    """Unit tests for write_feedback_files (Req 6.5, 6.6)."""

    def test_writes_correct_count(self, tmp_path) -> None:
        groups = [
            _group_feedback(),
            GroupFeedback(
                group_name="Team Beta",
                students=(_BOB,),
                assignments=(
                    AssignmentEntry(
                        assignment_name="HW1",
                        submission_date=date(2025, 3, 1),
                        rubric=_rubric(),
                    ),
                ),
            ),
        ]
        count = write_feedback_files(groups, str(tmp_path))
        assert count == 2

    def test_creates_correct_filenames(self, tmp_path) -> None:
        groups = [_group_feedback()]
        write_feedback_files(groups, str(tmp_path))
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "team-alpha.md"

    def test_file_content_matches_render(self, tmp_path) -> None:
        gf = _group_feedback()
        write_feedback_files([gf], str(tmp_path))
        content = (tmp_path / "team-alpha.md").read_text(encoding="utf-8")
        assert content == render_group_markdown(gf)

    def test_creates_output_dir_if_missing(self, tmp_path) -> None:
        out = tmp_path / "nested" / "output"
        write_feedback_files([_group_feedback()], str(out))
        assert out.exists()
        assert len(list(out.iterdir())) == 1
