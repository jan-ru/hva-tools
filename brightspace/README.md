# Brightspace Feedback Extractor

A CLI tool that extracts rubric feedback from [Brightspace DLO](https://www.d2l.com/) using Playwright. It connects to a browser where you've already logged in, scrapes rubric scores and comments for student groups across assignments, and writes one markdown file per group.

## Why?

Brightspace doesn't offer a convenient way to export rubric feedback in bulk. This tool automates the tedious click-through process so you can review, share, or archive feedback outside the LMS.

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- A Chromium-based browser with remote debugging enabled

### Install

```bash
uv sync
```

### Launch your browser with remote debugging

```bash
# Chrome/Chromium example
chrome --remote-debugging-port=9222
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

### Example

```bash
brightspace-extractor extract 12345 67890 67891 --output-dir ./feedback
```

This produces one `.md` file per group in `./feedback/`, e.g.:

```
feedback/
├── team-alpha.md
├── team-beta.md
└── team-gamma.md
```

## Output Format

Each markdown file contains:

- Group name as heading
- Student names
- Per-assignment rubric table (criterion, score, feedback) ordered chronologically

See [docs/output-format.md](docs/output-format.md) for a full example.

## Architecture

The tool follows a functional data pipeline:

```
browser → extract raw data → parse into models → aggregate by group → serialize to markdown → write files
```

- Pure core: `models.py`, `parsing.py`, `aggregation.py`, `serialization.py` — no I/O, no mutation
- Impure edges: `browser.py`, `navigation.py`, `extraction.py` — Playwright interaction
- Orchestration: `cli.py` — wires everything together

All domain models are immutable Pydantic `BaseModel(frozen=True)` instances.

See [docs/architecture.md](docs/architecture.md) for details.

## Development

```bash
# Install with dev dependencies
uv sync

# Run tests
uv run pytest

# Run only property-based tests
uv run pytest -k "property"
```

## Error Handling

- Setup errors (connection, auth, class not found) → fail fast with exit code 1
- Per-item errors (missing assignment, timeout, missing rubric) → log warning, skip, continue

## License

Not yet specified.
