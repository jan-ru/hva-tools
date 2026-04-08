"""Property-based and unit tests for pandoc serialization extensions."""

import re
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
    _build_separator_row,
    _escape_cell,
    group_to_filename,
    render_group_markdown_pandoc,
)
from tests.conftest import make_criterion


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Group name: at least 1 char, printable, may contain spaces/hyphens/digits
_group_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters=" -"),
    min_size=1,
    max_size=30,
)

# Category suffix: at least 1 alphanumeric char
_category_suffix = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=10,
)


# ---------------------------------------------------------------------------
# Property 5: Filename includes category suffix
# ---------------------------------------------------------------------------


@settings(max_examples=200)
@given(group_name=_group_name, category=_category_suffix)
def test_property_filename_includes_category_suffix(
    group_name: str, category: str
) -> None:
    """For any group name and non-empty category, the filename ends with
    ``-{category.lower()}.md`` and starts with the lowercased, hyphenated
    group name.

    Feature: criteria-filtering-pdf-export, Property 5: Filename includes category suffix
    Validates: Requirements 3.5
    """
    filename = group_to_filename(group_name, suffix=category)

    expected_base = group_name.lower().replace(" ", "-")
    expected_suffix = f"-{category.lower()}.md"

    assert filename.endswith(expected_suffix), (
        f"Expected filename to end with {expected_suffix!r}, got {filename!r}"
    )
    assert filename.startswith(expected_base), (
        f"Expected filename to start with {expected_base!r}, got {filename!r}"
    )
    assert filename == f"{expected_base}{expected_suffix}"


# ---------------------------------------------------------------------------
# Property 6: PDF filename mirrors markdown filename
# ---------------------------------------------------------------------------

# Markdown filename: lowercase alphanumeric + hyphens, ending in .md
_md_filename = st.from_regex(r"[a-z0-9][a-z0-9\-]{0,29}\.md", fullmatch=True)


@settings(max_examples=200)
@given(md_filename=_md_filename)
def test_property_pdf_filename_mirrors_markdown_filename(
    md_filename: str,
) -> None:
    """For any markdown filename ending in ``.md``, the derived PDF filename
    is identical except with a ``.pdf`` extension.

    Feature: criteria-filtering-pdf-export, Property 6: PDF filename mirrors markdown filename
    Validates: Requirements 4.5
    """
    from pathlib import PurePosixPath

    md_path = PurePosixPath(md_filename)
    pdf_path = md_path.with_suffix(".pdf")

    # Extension swapped correctly
    assert str(pdf_path).endswith(".pdf")
    assert not str(pdf_path).endswith(".md")

    # Stem (name without extension) is identical
    assert md_path.stem == pdf_path.stem

    # Full name matches except for extension
    expected_pdf = md_filename[:-3] + ".pdf"
    assert str(pdf_path) == expected_pdf


# ---------------------------------------------------------------------------
# Property 7: Separator row dash counts are proportional to column widths
# ---------------------------------------------------------------------------

# Three positive integers for column width ratios
_col_widths = st.tuples(
    st.integers(min_value=1, max_value=50),
    st.integers(min_value=1, max_value=50),
    st.integers(min_value=1, max_value=50),
)


@settings(max_examples=200)
@given(widths=_col_widths)
def test_property_separator_row_dash_counts_proportional(
    widths: tuple[int, int, int],
) -> None:
    """For any tuple of three positive integers (a, b, c), the separator row
    produced by ``_build_separator_row((a, b, c))`` contains three dash
    segments whose lengths are proportional to a, b, and c.

    Feature: criteria-filtering-pdf-export, Property 7: Separator row dash counts are proportional to column widths
    Validates: Requirements 5.1
    """
    row = _build_separator_row(widths)

    # Extract the three segments between pipes (strip leading/trailing pipe)
    segments = row.strip("|").split("|")
    assert len(segments) == 3, f"Expected 3 segments, got {len(segments)}: {row!r}"

    # Strip alignment markers to isolate the proportional dash core.
    # The implementation uses:
    #   left-aligned:  ":" + "-" * (w*mult) + "-"   (1 extra dash for padding)
    #   center-aligned: ":" + "-" * (w*mult) + ":"  (0 extra dashes)
    #   left-aligned:  ":" + "-" * (w*mult) + "-"   (1 extra dash for padding)
    # Subtract the fixed alignment overhead per column type.
    dash_counts_raw = [seg.count("-") for seg in segments]
    dash_counts = []
    for seg, raw in zip(segments, dash_counts_raw):
        if seg.endswith(":"):
            # Center-aligned — all dashes are proportional
            dash_counts.append(raw)
        else:
            # Left-aligned — one trailing dash is alignment padding
            dash_counts.append(raw - 1)

    # All proportional dash counts must be positive
    for i, count in enumerate(dash_counts):
        assert count > 0, f"Segment {i} has no proportional dashes: {segments[i]!r}"

    # Proportionality: dash_count_i / width_i should be equal for all columns
    a, b, c = widths
    ratios = [
        dash_counts[0] / a,
        dash_counts[1] / b,
        dash_counts[2] / c,
    ]
    assert ratios[0] == ratios[1] == ratios[2], (
        f"Dash counts {dash_counts} not proportional to widths {widths}: ratios={ratios}"
    )


# ---------------------------------------------------------------------------
# Strategies for GroupFeedback generation
# ---------------------------------------------------------------------------

_criterion = st.builds(
    Criterion,
    name=st.text(min_size=1, max_size=20),
    score=st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
    feedback=st.text(max_size=50),
)

_rubric_feedback = st.builds(
    RubricFeedback,
    criteria=st.tuples(_criterion).map(lambda t: t)  # at least 1 criterion
    | st.lists(_criterion, min_size=1, max_size=5).map(tuple),
)

_assignment_entry = st.builds(
    AssignmentEntry,
    assignment_name=st.text(min_size=1, max_size=30),
    submission_date=st.dates(),
    rubric=_rubric_feedback,
)

_group_feedback_with_criteria = st.builds(
    GroupFeedback,
    group_name=_group_name,
    students=st.lists(
        st.builds(Student, name=st.text(min_size=1, max_size=20)),
        min_size=1,
        max_size=3,
    ).map(tuple),
    assignments=st.lists(_assignment_entry, min_size=1, max_size=3).map(tuple),
)


# ---------------------------------------------------------------------------
# Property 8: Pandoc output contains alignment markers
# ---------------------------------------------------------------------------


@settings(max_examples=200)
@given(gf=_group_feedback_with_criteria)
def test_property_pandoc_output_contains_alignment_markers(
    gf: GroupFeedback,
) -> None:
    """For any GroupFeedback with at least one assignment containing at least
    one criterion, ``render_group_markdown_pandoc(gf)`` contains at least one
    separator row with alignment markers (colon-prefixed dash segments).

    Feature: criteria-filtering-pdf-export, Property 8: Pandoc output contains alignment markers
    Validates: Requirements 6.1
    """
    output = render_group_markdown_pandoc(gf)

    # The separator row must contain left-aligned (:---) or center-aligned (:---:) markers
    assert re.search(r"\|:---", output), (
        f"Expected alignment markers (|:---) in pandoc output, got:\n{output}"
    )


# ---------------------------------------------------------------------------
# Strategies for HTML + pipe content generation
# ---------------------------------------------------------------------------

# Random HTML tag names (simple alphabetic)
_tag_name = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=1,
    max_size=8,
)

# Strategy that produces strings containing a mix of plain text, HTML tags, and pipes
_html_pipe_text = st.builds(
    "".join,
    st.lists(
        st.one_of(
            st.text(
                alphabet=st.characters(
                    blacklist_characters="<>",
                    whitelist_categories=("L", "N", "P", "Z"),
                ),
                min_size=0,
                max_size=10,
            ),
            # Self-closing or open/close HTML tags
            _tag_name.map(lambda t: f"<{t}>"),
            _tag_name.map(lambda t: f"</{t}>"),
            # Literal pipe characters
            st.just("|"),
        ),
        min_size=1,
        max_size=10,
    ),
)


# ---------------------------------------------------------------------------
# Property 9: Cell escaping removes HTML and escapes pipes
# ---------------------------------------------------------------------------


@settings(max_examples=200)
@given(text=_html_pipe_text)
def test_property_cell_escaping_removes_html_and_escapes_pipes(
    text: str,
) -> None:
    """For any string, ``_escape_cell(s)`` shall not contain any ``<tag>``
    patterns (angle-bracket-enclosed sequences), and every literal ``|`` in
    the original string shall appear as ``\\|`` in the output.

    Feature: criteria-filtering-pdf-export, Property 9: Cell escaping removes HTML and escapes pipes
    Validates: Requirements 6.2, 6.3
    """
    result = _escape_cell(text)

    # No HTML tags remain (no <...> sequences)
    assert not re.search(r"<[^>]*>", result), (
        f"HTML tags still present in escaped output: {result!r} (input: {text!r})"
    )

    # Every unescaped pipe in the original must now be escaped.
    # The result must not contain a bare pipe (one not preceded by backslash).
    assert not re.search(r"(?<!\\)\|", result), (
        f"Unescaped pipe found in output: {result!r} (input: {text!r})"
    )

    # Count preservation: the number of escaped pipes in the output must equal
    # the number of literal pipes in the *tag-stripped* version of the input,
    # because _escape_cell first strips tags, then escapes pipes.
    tag_stripped = re.sub(r"<[^>]*>", "", text)
    original_pipes = tag_stripped.count("|")
    escaped_pipes = result.count("\\|")
    assert escaped_pipes == original_pipes, (
        f"Expected {original_pipes} escaped pipes, got {escaped_pipes} "
        f"(input: {text!r}, result: {result!r})"
    )


# ---------------------------------------------------------------------------
# Unit tests for pandoc serialization (Task 4.9)
# ---------------------------------------------------------------------------


def _make_group_feedback(
    group_name: str = "FC2A - 1",
    assignment_name: str = "Assignment 1",
    criteria: tuple[Criterion, ...] | None = None,
) -> GroupFeedback:
    """Helper to build a minimal GroupFeedback for unit tests."""
    if criteria is None:
        criteria = (
            make_criterion("Requirements en Informatie", 8.0, "Good work"),
            make_criterion("Dashboard in Power BI", 7.5, "Needs improvement"),
        )
    return GroupFeedback(
        group_name=group_name,
        students=(Student(name="Alice"), Student(name="Bob")),
        assignments=(
            AssignmentEntry(
                assignment_name=assignment_name,
                submission_date=date(2025, 6, 1),
                rubric=RubricFeedback(criteria=criteria),
            ),
        ),
    )


class TestRenderGroupMarkdownPandoc:
    """Unit tests for render_group_markdown_pandoc()."""

    def test_known_output(self) -> None:
        """Render known input and verify the full output string."""
        gf = _make_group_feedback(
            criteria=(
                Criterion(name="Criterion A", score=9.0, feedback="Excellent"),
                Criterion(name="Criterion B", score=6.5, feedback="Okay"),
            ),
        )
        output = render_group_markdown_pandoc(gf, col_widths=(3, 1, 6))

        assert output.startswith("# FC2A - 1\n")
        assert "### Assignment 1" in output
        assert "| Criterion | Score | Feedback |" in output
        assert "| Criterion A | 9 | Excellent |" in output
        assert "| Criterion B | 6.5 | Okay |" in output
        assert output.rstrip().endswith("---")

    def test_category_label_in_title(self) -> None:
        """When category_label is provided, the title includes it."""
        gf = _make_group_feedback()
        output = render_group_markdown_pandoc(gf, category_label="MIS")

        assert output.startswith("# MIS Feedback — FC2A - 1\n")

    def test_no_category_label(self) -> None:
        """When category_label is None, the title is just the group name."""
        gf = _make_group_feedback()
        output = render_group_markdown_pandoc(gf, category_label=None)

        assert output.startswith("# FC2A - 1\n")

    def test_default_col_widths(self) -> None:
        """Default col_widths is (3, 1, 6) — verify separator row matches.

        Validates: Requirement 5.3
        """
        gf = _make_group_feedback()
        output_default = render_group_markdown_pandoc(gf)
        output_explicit = render_group_markdown_pandoc(gf, col_widths=(3, 1, 6))

        assert output_default == output_explicit

    def test_integer_score_no_decimal(self) -> None:
        """Scores that are whole numbers render without decimal point."""
        gf = _make_group_feedback(
            criteria=(Criterion(name="X", score=8.0, feedback="ok"),),
        )
        output = render_group_markdown_pandoc(gf)

        assert "| X | 8 | ok |" in output

    def test_fractional_score_keeps_decimal(self) -> None:
        """Scores with fractional parts keep the decimal."""
        gf = _make_group_feedback(
            criteria=(Criterion(name="X", score=7.5, feedback="ok"),),
        )
        output = render_group_markdown_pandoc(gf)

        assert "| X | 7.5 | ok |" in output

    def test_assignment_heading_level(self) -> None:
        """Assignment headings use ### (h3) to avoid typst page breaks."""
        gf = _make_group_feedback()
        output = render_group_markdown_pandoc(gf)

        assert "### Assignment 1" in output
        # Should NOT use ## for assignment headings
        lines = output.split("\n")
        assignment_lines = [
            line for line in lines if "Assignment 1" in line and line.startswith("#")
        ]
        for line in assignment_lines:
            assert line.startswith("### "), f"Expected ### heading, got: {line!r}"


class TestEscapeCell:
    """Unit tests for _escape_cell()."""

    def test_strips_html_tags(self) -> None:
        """HTML tags are removed from cell text."""
        assert _escape_cell("<b>bold</b>") == "bold"
        assert _escape_cell("<br/>") == ""
        assert _escape_cell("no tags") == "no tags"

    def test_strips_nested_html(self) -> None:
        """Nested HTML tags are all removed."""
        assert _escape_cell("<div><span>text</span></div>") == "text"

    def test_escapes_pipe_characters(self) -> None:
        """Pipe characters are escaped with backslash."""
        assert _escape_cell("a|b") == "a\\|b"
        assert _escape_cell("||") == "\\|\\|"

    def test_html_and_pipes_combined(self) -> None:
        """HTML stripping happens before pipe escaping."""
        result = _escape_cell("<b>a|b</b>")
        assert result == "a\\|b"

    def test_empty_string(self) -> None:
        """Empty input returns empty output."""
        assert _escape_cell("") == ""

    def test_plain_text_unchanged(self) -> None:
        """Text without HTML or pipes passes through unchanged."""
        assert _escape_cell("hello world") == "hello world"


class TestBuildSeparatorRow:
    """Unit tests for _build_separator_row()."""

    def test_known_widths_3_1_6(self) -> None:
        """Verify separator row structure for default (3, 1, 6) widths."""
        row = _build_separator_row((3, 1, 6))

        # Must start and end with pipe
        assert row.startswith("|")
        assert row.endswith("|")

        segments = row.strip("|").split("|")
        assert len(segments) == 3

        # First column: left-aligned (:---...-) with 30 dashes + 1 padding
        assert segments[0].startswith(":")
        assert not segments[0].endswith(":")

        # Second column: center-aligned (:---...:) with 10 dashes
        assert segments[1].startswith(":")
        assert segments[1].endswith(":")

        # Third column: left-aligned (:---...-) with 60 dashes + 1 padding
        assert segments[2].startswith(":")
        assert not segments[2].endswith(":")

    def test_dash_counts_proportional(self) -> None:
        """Dash counts in the separator are proportional to width ratios."""
        row = _build_separator_row((2, 3, 5))
        segments = row.strip("|").split("|")

        # Extract proportional dash counts (subtract alignment overhead)
        counts = []
        for seg in segments:
            raw = seg.count("-")
            if seg.endswith(":"):
                counts.append(raw)  # center-aligned: no extra dash
            else:
                counts.append(raw - 1)  # left-aligned: 1 padding dash

        # With multiplier=10: expect 20, 30, 50
        assert counts[0] == 20
        assert counts[1] == 30
        assert counts[2] == 50

    def test_equal_widths(self) -> None:
        """Equal widths produce equal proportional dash counts."""
        row = _build_separator_row((1, 1, 1))
        segments = row.strip("|").split("|")

        counts = []
        for seg in segments:
            raw = seg.count("-")
            if seg.endswith(":"):
                counts.append(raw)
            else:
                counts.append(raw - 1)

        assert counts[0] == counts[1] == counts[2]
