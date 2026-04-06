"""Pure functions to serialize GroupFeedback into markdown strings and write files."""

from pathlib import Path

from brightspace_extractor.models import GroupFeedback


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

    # Per-assignment sections
    for entry in group_feedback.assignments:
        lines.append(f"## {entry.assignment_name}")
        lines.append("")
        lines.append(f"**Date:** {entry.submission_date.isoformat()}")
        lines.append("")

        # Rubric criteria table
        lines.append("| Criterion | Score | Feedback |")
        lines.append("|---|---|---|")
        for criterion in entry.rubric.criteria:
            # Escape pipe characters in text fields
            name = criterion.name.replace("|", "\\|")
            feedback = criterion.feedback.replace("|", "\\|")
            lines.append(f"| {name} | {criterion.score} | {feedback} |")
        lines.append("")

    return "\n".join(lines)


def group_to_filename(group_name: str) -> str:
    """Derive filename from group name: lowercase, spaces to hyphens, .md extension."""
    return group_name.lower().replace(" ", "-") + ".md"


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
