# CLI Commands

All commands share these options:

| Flag | Default | Description |
|---|---|---|
| `--config` | `config/brightspace.toml` | Path to TOML config file |
| `--cdp-url` | `http://localhost:9222` | Chrome DevTools Protocol endpoint |
| `--base-url` | `https://dlo.mijnhva.nl` | Brightspace instance base URL |

## courses

List enrolled courses (class IDs) from the Brightspace homepage.

```bash
brightspace-extractor courses
```

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | — | Write a `courses.md` file to this directory |

## assignments

List assignments (dropbox folders) for a class.

```bash
brightspace-extractor assignments CLASS_ID
```

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | — | Write an `assignments.md` file to this directory |

> **Note:** Assignment IDs are the dropbox folder IDs (`db=XXXXXX` in the URL), not the activity iterator IDs.

## classlist

List students enrolled in a class.

```bash
brightspace-extractor classlist CLASS_ID
```

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | — | Write a `classlist.md` file to this directory |
| `--role` | `Student` | Filter by role (e.g. `Student`, `Designing Lecturer`). Pass `--role=""` for all |

## groups

List groups and their members for a class.

```bash
brightspace-extractor groups CLASS_ID
```

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | — | Write a `groups.md` file to this directory |

## quizzes

List quizzes for a class.

```bash
brightspace-extractor quizzes CLASS_ID
```

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | — | Write a `quizzes.md` file to this directory |

## rubrics

List rubrics for a class.

```bash
brightspace-extractor rubrics CLASS_ID
```

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | — | Write a `rubrics.md` file to this directory |

## extract

Extract rubric feedback for specified class and assignments.

```bash
brightspace-extractor extract CLASS_ID ASSIGNMENT_ID_1 ASSIGNMENT_ID_2 ...
```

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | `./output` | Directory for generated markdown files |
| `--category` | — | Category name to filter rubric criteria (requires `--category-config`) |
| `--category-config` | — | Path to TOML file mapping category names to criterion patterns |
| `--pdf` | `false` | Generate PDF output via pandoc + typst |
| `--col-widths` | `3,1,6` | Column width ratios for PDF tables (three comma-separated integers) |
| `--combined` | `false` | Also produce a single combined PDF of all groups |

### Examples

Basic extraction:

```bash
brightspace-extractor extract 12345 67890 67891 --output-dir ./feedback
```

Filtered PDF export for a specific category:

```bash
brightspace-extractor extract 12345 67890 67891 \
  --category MIS \
  --category-config categories.toml \
  --pdf \
  --col-widths 3,1,6 \
  --output-dir ./feedback
```

This produces one `.md` (and optionally `.pdf`) file per group:

```
feedback/
├── team-alpha.md
├── team-alpha.pdf
├── team-beta.md
├── team-beta.pdf
└── ...
```
