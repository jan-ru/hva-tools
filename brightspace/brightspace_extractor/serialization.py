"""Pure functions to serialize GroupFeedback into markdown strings and write files."""

import re
from pathlib import Path

from brightspace_extractor.models import GroupFeedback


def _escape_cell(text: str) -> str:
    """Strip HTML tags and escape pipe characters in cell text."""
    stripped = re.sub(r"<[^>]*>", "", text)
    return stripped.replace("|", "\\|")


def _format_score(score: float) -> str:
    """Format a score: drop .0 for whole numbers, keep decimals otherwise."""
    return str(int(score)) if score == int(score) else str(score)


def _build_separator_row(col_widths: tuple[int, int, int]) -> str:
    """Build a pandoc pipe table separator row with alignment markers.

    col_widths are relative ratios. Dashes are proportional to the ratios
    using a multiplier of 10 (e.g. (3,1,6) → ~30, 10, 60 dashes).
    First column left-aligned (:---), second centered (:---:), third left-aligned (:---).
    """
    multiplier = 10
    left = ":" + "-" * (col_widths[0] * multiplier) + "-"
    center = ":" + "-" * (col_widths[1] * multiplier) + ":"
    right = ":" + "-" * (col_widths[2] * multiplier) + "-"
    return f"|{left}|{center}|{right}|"


def _render_criteria_table(
    rubric,
    separator: str = "|---|---|---|",
    *,
    escape_html: bool = False,
    format_int_scores: bool = False,
) -> list[str]:
    """Render a rubric criteria table as markdown lines.

    Args:
        rubric: A RubricFeedback instance.
        separator: The separator row between header and body.
        escape_html: If True, strip HTML tags from cell content.
        format_int_scores: If True, render whole-number scores without decimals.
    """
    lines: list[str] = []
    lines.append("| Criterion | Score | Feedback |")
    lines.append(separator)
    for criterion in rubric.criteria:
        name = (
            _escape_cell(criterion.name)
            if escape_html
            else criterion.name.replace("|", "\\|")
        )
        feedback = (
            _escape_cell(criterion.feedback)
            if escape_html
            else criterion.feedback.replace("|", "\\|")
        )
        score = (
            _format_score(criterion.score)
            if format_int_scores
            else str(criterion.score)
        )
        lines.append(f"| {name} | {score} | {feedback} |")
    return lines


def render_group_markdown_pandoc(
    group_feedback: GroupFeedback,
    col_widths: tuple[int, int, int] = (3, 1, 6),
    category_label: str | None = None,
) -> str:
    """Render GroupFeedback as pandoc-compatible markdown.

    Differences from standard render:
    - Title includes category label (e.g., "MIS Feedback \u2014 Group Name")
    - Pipe tables use alignment markers in separator row
    - Column widths encoded via padding in separator row
    - HTML tags stripped from cell content
    - Pipe characters in cells escaped
    - Uses ### for assignment headings (not ##) to avoid typst page breaks
    """
    lines: list[str] = []

    # Title with optional category label
    if category_label:
        lines.append(f"# {category_label} Feedback \u2014 {group_feedback.group_name}")
    else:
        lines.append(f"# {group_feedback.group_name}")
    lines.append("")
    lines.append("")

    separator = _build_separator_row(col_widths)

    for entry in group_feedback.assignments:
        lines.append(f"### {entry.assignment_name}")
        lines.append("")
        lines.extend(
            _render_criteria_table(
                entry.rubric,
                separator,
                escape_html=True,
                format_int_scores=True,
            )
        )
        lines.append("")

    # Trailing horizontal rule
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def render_group_markdown(group_feedback: GroupFeedback) -> str:
    """Render a GroupFeedback into a markdown string.

    The output contains:
    - Group name as a top-level heading
    - Student names
    - Per-assignment sections with name, date, and a rubric criteria table
    """
    lines: list[str] = []

    # Group heading
    lines.append(f"# {group_feedback.group_name}")
    lines.append("")

    # Student names
    student_names = ", ".join(s.name for s in group_feedback.students)
    lines.append(f"**Students:** {student_names}")
    lines.append("")

    for entry in group_feedback.assignments:
        lines.append(f"## {entry.assignment_name}")
        lines.append("")
        lines.append(f"**Date:** {entry.submission_date.isoformat()}")
        lines.append("")
        lines.extend(_render_criteria_table(entry.rubric))
        lines.append("")

    return "\n".join(lines)


def group_to_filename(group_name: str, suffix: str | None = None) -> str:
    """Derive filename from group name: lowercase, spaces to hyphens, .md extension.

    When *suffix* is provided, ``-{suffix.lower()}`` is appended before the
    ``.md`` extension (e.g. ``group_to_filename("FC2A - 1", suffix="MIS")``
    \u2192 ``"fc2a---1-mis.md"``).
    """
    base = group_name.lower().replace(" ", "-")
    if suffix:
        base = f"{base}-{suffix.lower()}"
    return base + ".md"


def write_feedback_files(groups: list[GroupFeedback], output_dir: str) -> int:
    """Write one markdown file per group to output_dir.

    Creates output_dir if it does not exist. Returns the count of files written.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    count = 0
    for gf in groups:
        filename = group_to_filename(gf.group_name)
        (out / filename).write_text(render_group_markdown(gf), encoding="utf-8")
        count += 1

    return count
