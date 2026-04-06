# Architecture

## Pipeline Overview

```
connect to browser
    → verify authentication
    → navigate to class
    → for each assignment:
        → navigate to submissions page
        → extract rubric data via Assessments API (list of dicts)
        → parse into Pydantic models
    → aggregate all feedback by group
    → render each group to markdown
    → write files to output directory
```

## Module Responsibilities

| Module | Pure/Impure | Role |
|---|---|---|
| `cli.py` | Orchestration | CLI parsing (cyclopts), pipeline wiring |
| `browser.py` | Impure | CDP connection, auth verification |
| `navigation.py` | Impure | Brightspace page navigation |
| `extraction.py` | Impure | Hypermedia API extraction → raw dicts |
| `models.py` | Pure | Pydantic frozen domain models |
| `parsing.py` | Pure | Raw dicts → validated models |
| `aggregation.py` | Pure | Group-level aggregation across assignments |
| `serialization.py` | Pure | Models → markdown strings, file writing |
| `exceptions.py` | Pure | Custom exception hierarchy |

## Domain Models

All models use `frozen=True` (immutable).

```
Student(name)
Criterion(name, score, feedback)
RubricFeedback(criteria: tuple[Criterion, ...])
GroupSubmission(group_name, students, rubric, submission_date)
AssignmentFeedback(assignment_name, assignment_id, submissions: tuple[GroupSubmission, ...])
AssignmentEntry(assignment_name, submission_date, rubric)
GroupFeedback(group_name, students, assignments: tuple[AssignmentEntry, ...])
```

## Data Flow

```
Raw dicts (from Assessments API)
    → parsing.py → GroupSubmission
    → collected per assignment → AssignmentFeedback
    → aggregation.py → GroupFeedback
    → serialization.py → markdown string
    → write to disk → .md file
```

## Error Strategy

| Error | Behavior |
|---|---|
| CDP unreachable | Exit 1 |
| Not authenticated | Exit 1 |
| Class not found | Exit 1 |
| Assignment not found | Warn + skip |
| Navigation timeout | Warn + skip |
| Missing API response | Warn + skip |
| No rubric for group | Warn + skip |

Setup errors fail fast. Per-item errors degrade gracefully so the tool extracts as much data as possible.

## Testing

- Unit tests: specific examples and edge cases for pure modules
- Property-based tests (Hypothesis): 4 correctness properties covering aggregation round-trips, chronological ordering, markdown completeness, and filename derivation
- All tests run with `uv run pytest`
