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

### Usage

```bash
# List enrolled courses (find class IDs)
brightspace-extractor courses

# List assignments for a class
brightspace-extractor assignments CLASS_ID

# List enrolled students
brightspace-extractor classlist CLASS_ID

# List groups
brightspace-extractor groups CLASS_ID

# List quizzes
brightspace-extractor quizzes CLASS_ID

# List rubrics
brightspace-extractor rubrics CLASS_ID

# Extract rubric feedback
brightspace-extractor extract CLASS_ID ASSIGNMENT_ID_1 ASSIGNMENT_ID_2 ...
```

Use `--config` to load per-course settings from a TOML file:

```bash
brightspace-extractor classlist --config "config/Data&Control.toml"
brightspace-extractor extract 698557 336741 336743 --category MIS --pdf --combined
```

See [docs/commands.md](docs/commands.md) for all options and examples.

## Documentation

| Document | Description |
|---|---|
| [docs/commands.md](docs/commands.md) | Full CLI reference with all flags and examples |
| [docs/configuration.md](docs/configuration.md) | Config files, environment variables, category filtering |
| [docs/architecture.md](docs/architecture.md) | Pipeline design, module responsibilities, data flow |
| [docs/output-format.md](docs/output-format.md) | Markdown output format with examples |
| [docs/entity-relationship.md](docs/entity-relationship.md) | Mermaid ER diagram of domain models |

## Development

```bash
uv sync                                          # install with dev dependencies
uv run pytest                                    # run tests
uv run pytest --cov=brightspace_extractor        # run with coverage
uv run pytest -k "property"                      # property-based tests only
```

## Error Handling

- Setup errors (connection, auth, class not found, bad config) → fail fast with exit code 1
- Per-item errors (missing assignment, timeout, missing rubric) → log warning, skip, continue

## License

MIT — see [LICENSE](LICENSE).
