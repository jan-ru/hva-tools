"""Pydantic frozen domain models for the feedback extraction pipeline."""

from datetime import date

from pydantic import BaseModel


class Student(BaseModel, frozen=True):
    """A student within a group."""

    name: str


class Criterion(BaseModel, frozen=True):
    """A single rubric criterion with score and optional feedback."""

    name: str
    score: float
    feedback: str  # empty string if no feedback


class RubricFeedback(BaseModel, frozen=True):
    """Complete rubric feedback for one group on one assignment."""

    criteria: tuple[Criterion, ...]


class GroupSubmission(BaseModel, frozen=True):
    """Raw extraction result for one group on one assignment."""

    group_name: str
    students: tuple[Student, ...]
    rubric: RubricFeedback
    submission_date: date


class AssignmentEntry(BaseModel, frozen=True):
    """One assignment's feedback within a GroupFeedback."""

    assignment_name: str
    submission_date: date
    rubric: RubricFeedback


class AssignmentFeedback(BaseModel, frozen=True):
    """All group submissions for a single assignment."""

    assignment_name: str
    assignment_id: str
    submissions: tuple[GroupSubmission, ...]


class GroupFeedback(BaseModel, frozen=True):
    """Aggregated feedback for a single group across all assignments."""

    group_name: str
    students: tuple[Student, ...]
    assignments: tuple[AssignmentEntry, ...]


# ---------------------------------------------------------------------------
# Discovery models (assignments, classlist, groups)
# ---------------------------------------------------------------------------


class AssignmentInfo(BaseModel, frozen=True):
    """A dropbox assignment visible in the class."""

    assignment_id: str
    name: str


class ClassMember(BaseModel, frozen=True):
    """A student enrolled in the class."""

    name: str
    username: str


class GroupInfo(BaseModel, frozen=True):
    """A group with its member names."""

    group_name: str
    category: str
    members: tuple[str, ...]


class CourseInfo(BaseModel, frozen=True):
    """A course (org unit) visible on the homepage."""

    class_id: str
    name: str
