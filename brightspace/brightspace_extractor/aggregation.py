"""Pure functions to aggregate feedback across assignments, grouped by student group."""

from collections import defaultdict

from brightspace_extractor.models import (
    AssignmentEntry,
    AssignmentFeedback,
    GroupFeedback,
)


def aggregate_by_group(feedbacks: list[AssignmentFeedback]) -> list[GroupFeedback]:
    """Aggregate AssignmentFeedback across assignments, grouped by group name.

    Orders assignments chronologically within each group.
    """
    # Collect per-group: students and assignment entries
    group_students: dict[str, tuple] = {}
    group_entries: dict[str, list[AssignmentEntry]] = defaultdict(list)

    for af in feedbacks:
        for sub in af.submissions:
            # Keep the first-seen student tuple per group
            if sub.group_name not in group_students:
                group_students[sub.group_name] = sub.students

            group_entries[sub.group_name].append(
                AssignmentEntry(
                    assignment_name=af.assignment_name,
                    submission_date=sub.submission_date,
                    rubric=sub.rubric,
                )
            )

    return [
        GroupFeedback(
            group_name=name,
            students=group_students[name],
            assignments=tuple(sorted(entries, key=lambda e: e.submission_date)),
        )
        for name, entries in group_entries.items()
    ]
