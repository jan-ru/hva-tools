"""Pure functions to parse raw extraction dicts into validated Pydantic models."""

from __future__ import annotations

import logging
from datetime import date

from pydantic import ValidationError

from brightspace_extractor.models import (
    AssignmentFeedback,
    Criterion,
    GroupSubmission,
    RubricFeedback,
    Student,
)

logger = logging.getLogger(__name__)


def parse_group_submission(raw: dict) -> GroupSubmission:
    """Parse a raw extraction dict into a validated GroupSubmission model.

    Expected dict shape::

        {
            "group_name": str,
            "students": [str, ...],
            "criteria": [{"name": str, "score": float, "feedback": str}, ...],
            "submission_date": "YYYY-MM-DD" | date,
        }

    Raises ``ValueError`` when required fields are missing or have wrong types.
    """
    try:
        group_name = raw["group_name"]
        students = tuple(Student(name=s) for s in raw["students"])
        criteria = tuple(
            Criterion(name=c["name"], score=c["score"], feedback=c.get("feedback", ""))
            for c in raw["criteria"]
        )
        rubric = RubricFeedback(criteria=criteria)
        submission_date = (
            raw["submission_date"]
            if isinstance(raw["submission_date"], date)
            else date.fromisoformat(raw["submission_date"])
        )
        return GroupSubmission(
            group_name=group_name,
            students=students,
            rubric=rubric,
            submission_date=submission_date,
        )
    except KeyError as exc:
        raise ValueError(f"Missing required field: {exc}") from exc
    except (TypeError, ValidationError) as exc:
        raise ValueError(f"Malformed submission data: {exc}") from exc


def parse_all_submissions(
    raws: list[dict],
    assignment_name: str,
    assignment_id: str,
) -> list[AssignmentFeedback]:
    """Parse all raw submissions for an assignment into AssignmentFeedback models.

    Each raw dict is parsed via :func:`parse_group_submission`.  Malformed entries
    are logged as warnings and skipped so that one bad group doesn't block the rest.

    Returns a single-element list containing the ``AssignmentFeedback`` (list for
    pipeline composability).  Returns an empty list when *all* entries fail parsing.
    """
    submissions: list[GroupSubmission] = []
    for raw in raws:
        try:
            submissions.append(parse_group_submission(raw))
        except ValueError:
            group_hint = raw.get("group_name", "<unknown>")
            logger.warning(
                "Skipping malformed submission for group '%s' in assignment '%s': "
                "could not parse raw data",
                group_hint,
                assignment_name,
            )

    if not submissions:
        return []

    return [
        AssignmentFeedback(
            assignment_name=assignment_name,
            assignment_id=assignment_id,
            submissions=tuple(submissions),
        )
    ]
