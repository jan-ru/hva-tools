"""Unit and property tests for markdown rendering."""

from datetime import date

from hypothesis import given, settings

from brightspace_extractor.models import (
    AssignmentEntry,
    GroupFeedback,
)
from brightspace_extractor.serialization import (
    render_group_markdown,
    write_feedback_files,
)
from tests.conftest import (
    ALICE,
    BOB,
    group_feedback_st,
    make_criterion,
    make_rubric,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _group_feedback() -> GroupFeedback:
    return GroupFeedback(
        group_name="Team Alpha",
        students=(ALICE, BOB),
        assignments=(
            AssignmentEntry(
                assignment_name="HW1",
                submission_date=date(2025, 3, 1),
                rubric=make_rubric(
                    make_criterion("Clarity", 9.0, "Very clear"),
                    make_criterion("Depth", 7.5, "Could go deeper"),
                ),
            ),
        ),
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
            students=(ALICE,),
            assignments=(
                AssignmentEntry(
                    assignment_name="HW1",
                    submission_date=date(2025, 1, 15),
                    rubric=make_rubric(make_criterion("A", 5.0, "ok")),
                ),
                AssignmentEntry(
                    assignment_name="HW2",
                    submission_date=date(2025, 2, 20),
                    rubric=make_rubric(make_criterion("B", 10.0, "great")),
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
                students=(BOB,),
                assignments=(
                    AssignmentEntry(
                        assignment_name="HW1",
                        submission_date=date(2025, 3, 1),
                        rubric=make_rubric(),
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
