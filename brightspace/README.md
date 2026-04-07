# Brightspace Feedback Extractor

A CLI tool that extracts rubric feedback from [Brightspace DLO](https://www.d2l.com/) using Playwright. It connects to a browser where you've already logged in, navigates to evaluation pages, and calls the Brightspace Assessments API to retrieve rubric scores and comments for student groups across assignments. Output is one markdown file per group, with optional PDF export via pandoc + typst.

## Why?

Brightspace doesn't offer a convenient way to export rubric feedback in bulk. This tool automates the tedious click-through process so you can review, share, or archive feedback outside the LMS.

## Quick Start

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- A Chromium-based browser (Edge, Chrome, Brave, …) with remote debugging enabled
- (Optional) [pandoc](https://pandoc.org/installing.html) + [typst](https://typst.app/) for PDF export

### Install

```bash
uv sync
```

### Launch your browser with remote debugging

```powershell
# Microsoft Edge (recommended)
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222

# Chrome (alternative)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

Then log in to Brightspace manually (SSO, 2FA, etc.). The tool connects to this session — it does not automate login.

### Run

```bash
brightspace-extractor extract CLASS_ID ASSIGNMENT_ID_1 ASSIGNMENT_ID_2 ...
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | `./output` | Directory for generated markdown files |
| `--cdp-url` | `http://localhost:9222` | Chrome DevTools Protocol endpoint |
| `--base-url` | `https://dlo.mijnhva.nl` | Brightspace instance base URL |
| `--category` | — | Category name to filter rubric criteria (requires `--category-config`) |
| `--category-config` | — | Path to TOML file mapping category names to criterion patterns |
| `--pdf` | `false` | Generate PDF output via pandoc + typst |
| `--col-widths` | `3,1,6` | Column width ratios for PDF tables (three comma-separated integers) |

> **Note:** Assignment IDs are the dropbox folder IDs (`db=XXXXXX` in the URL), not the activity iterator IDs. Navigate to the Assignments page in Brightspace and look at the submission links to find them.

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

This produces one `.md` (and optionally `.pdf`) file per group in `./feedback/`:

```
feedback/
├── team-alpha.md
├── team-alpha.pdf
├── team-beta.md
├── team-beta.pdf
└── ...
```

## Category Filtering

You can filter rubric criteria by category using a TOML config file. Each category maps to a list of substring patterns matched case-insensitively against criterion names:

```toml
[categories]
MIS = ["informatie behoefte", "Dashboard", "Cloud"]
MAC = ["kostprijs", "budget omzet"]
```

Use `--category MIS --category-config categories.toml` to include only criteria matching the MIS patterns.

## Output Format

Each markdown file contains:

- Group name as heading
- Student names
- Per-assignment rubric table (criterion, score, feedback) ordered chronologically

See [docs/output-format.md](docs/output-format.md) for a full example.

## Architecture

The tool follows a functional data pipeline:

```
browser → extract via Assessments API → parse into models → filter (optional) → aggregate by group → serialize to markdown/PDF → write files
```

- Pure core: `models.py`, `parsing.py`, `aggregation.py`, `serialization.py`, `filtering.py` — no I/O, no mutation
- Impure edges: `browser.py`, `navigation.py`, `extraction.py`, `pdf_export.py` — Playwright interaction, subprocess calls
- Orchestration: `cli.py` — wires everything together

All domain models are immutable Pydantic `BaseModel(frozen=True)` instances.

See [docs/architecture.md](docs/architecture.md) for details.

## Development

```bash
# Install with dev dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=brightspace_extractor

# Run only property-based tests
uv run pytest -k "property"

# Git hooks (using prek, a fast Rust-based pre-commit replacement)
uv tool install prek
prek install
```

## Error Handling

- Setup errors (connection, auth, class not found, bad config) → fail fast with exit code 1
- Per-item errors (missing assignment, timeout, missing rubric) → log warning, skip, continue

## License

Not yet specified.
