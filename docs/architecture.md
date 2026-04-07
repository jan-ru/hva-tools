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
    → filter criteria by category (optional)
    → aggregate all feedback by group
    → render each group to markdown
    → write files to output directory (+ PDF via pandoc/typst if requested)
```

## CLI Commands

| Command | Purpose |
|---|---|
| `courses` | List enrolled courses from the Brightspace homepage |
| `assignments` | List assignments (dropbox folders) for a class |
| `classlist` | List students enrolled in a class |
| `groups` | List groups and members for a class |
| `quizzes` | List quizzes for a class |
| `rubrics` | List rubrics for a class |
| `extract` | Extract rubric feedback and produce markdown/PDF output |

All commands support a `--config` flag to load shared parameters from a TOML file (`config/brightspace.toml` by default). See the README for details.

## Module Responsibilities

| Module | Pure/Impure | Role |
|---|---|---|
| `cli.py` | Orchestration | CLI parsing (cyclopts), config loading, pipeline wiring |
| `browser.py` | Impure | CDP connection, auth verification |
| `navigation.py` | Impure | Brightspace page navigation |
| `extraction.py` | Impure | Assessments API extraction; HTML scraping for discovery commands |
| `models.py` | Pure | Pydantic frozen domain models |
| `parsing.py` | Pure | Raw dicts → validated models |
| `aggregation.py` | Pure | Group-level aggregation across assignments |
| `filtering.py` | Pure | Category-based criterion filtering |
| `serialization.py` | Pure | Models → markdown strings, file writing |
| `pdf_export.py` | Impure | Pandoc + typst PDF generation (per-group and combined) |
| `exceptions.py` | Pure | Custom exception hierarchy |

## Domain Models

All models use `frozen=True` (immutable). See [entity-relationship.md](entity-relationship.md) for a diagram.

Pipeline models:
```
Student(name)
Criterion(name, score, feedback)
RubricFeedback(criteria: tuple[Criterion, ...])
GroupSubmission(group_name, students, rubric, submission_date)
AssignmentFeedback(assignment_name, assignment_id, submissions)
AssignmentEntry(assignment_name, submission_date, rubric)
GroupFeedback(group_name, students, assignments)
```

Discovery models:
```
CourseInfo(class_id, name)
AssignmentInfo(assignment_id, name)
ClassMember(name, org_defined_id, role)
GroupInfo(group_name, category, members)
QuizInfo(quiz_id, name)
RubricInfo(rubric_id, name, rubric_type, scoring_method, status)
```

## Data Flow

```
Raw dicts (from Assessments API)
    → parsing.py → GroupSubmission
    → collected per assignment → AssignmentFeedback
    → filtering.py (optional) → filtered AssignmentFeedback
    → aggregation.py → GroupFeedback
    → serialization.py → markdown string
    → write to disk → .md file
    → pdf_export.py (optional) → .pdf per group + combined .pdf
```

## Configuration

The CLI loads shared parameters from `config/brightspace.toml` (or a path given via `--config`). Parameters can also be set via environment variables with a `BRIGHTSPACE_` prefix. Resolution order: CLI flag → env var → config file → built-in default.

Supported config keys: `class_id`, `base_url`, `cdp_url`, `output_dir`, `category_config`.

## Error Strategy

| Error | Behavior |
|---|---|
| CDP unreachable | Exit 1 |
| Not authenticated | Exit 1 |
| Class not found | Exit 1 |
| Config file malformed | Exit 1 |
| Assignment not found | Warn + skip |
| Navigation timeout | Warn + skip |
| Missing API response | Warn + skip |
| No rubric for group | Warn + skip |
| Combined PDF failure | Warn (per-group PDFs still produced) |

Setup errors fail fast. Per-item errors degrade gracefully so the tool extracts as much data as possible.

## Testing

- Unit tests: specific examples and edge cases for pure modules
- Property-based tests (Hypothesis): correctness properties covering aggregation round-trips, chronological ordering, markdown completeness, filename derivation, filtering, and pandoc output
- Config and model tests: validation of config loading, parameter resolution, and discovery models
- All tests run with `uv run pytest`
