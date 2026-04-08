# Brightspace Feedback Extractor

Extract rubric feedback from [Brightspace DLO](https://www.d2l.com/) in bulk. Two interfaces:

- **CLI** — connects to a local browser via CDP, navigates evaluation pages, calls the Brightspace Assessments API to retrieve rubric scores and comments. Output is one markdown file per group, with optional PDF export via pandoc + typst.
- **Browser extension + API** — a Manifest V3 extension captures page HTML from your authenticated Brightspace session and sends it to a FastAPI backend, which returns structured JSON, markdown, or PDF. No local Python needed for end users.

## Why?

Brightspace doesn't offer a convenient way to export rubric feedback in bulk. This tool automates the tedious click-through process so you can review, share, or archive feedback outside the LMS.

## Quick Start — CLI

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

1. Close all browser windows first (including background processes in the system tray). The `--remote-debugging-port` flag only works if the browser is fully closed.

2. Launch the browser with remote debugging enabled:

```powershell
# Microsoft Edge (recommended)
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222

# Chrome (alternative)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

3. Log in to Brightspace manually (SSO, 2FA, etc.), then run the tool. It connects to this session — it does not automate login.

> Tip: verify the debug port is active by opening http://localhost:9222 in another browser.

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

## Quick Start — API + Browser Extension

### Run the API

```bash
docker compose up -d
```

The API is available at `http://localhost:8000`. Verify:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Install the extension

1. Open `chrome://extensions` (or `edge://extensions`)
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `extension/` directory
4. Navigate to any Brightspace page and click the extension icon

The extension detects the page type, captures the HTML, sends it to the API, and displays results in a popup. Configure the API URL in the extension's options page.

See [docs/api.md](docs/api.md) for endpoint details and [docs/configuration.md](docs/configuration.md) for Docker and extension settings.

## Documentation

| Document | Description |
|---|---|
| [docs/commands.md](docs/commands.md) | Full CLI reference with all flags and examples |
| [docs/api.md](docs/api.md) | API endpoint reference (health, listing, extract) |
| [docs/configuration.md](docs/configuration.md) | Config files, environment variables, Docker, extension settings |
| [docs/architecture.md](docs/architecture.md) | Dual-interface architecture, module responsibilities, data flow |
| [docs/output-format.md](docs/output-format.md) | Markdown output format with examples |
| [docs/entity-relationship.md](docs/entity-relationship.md) | Mermaid ER diagram of domain models |
| [docs/future.md](docs/future.md) | Potential future improvements |
| [docs/security.md](docs/security.md) | Security considerations and hardening steps |

## Development

```bash
uv sync                                          # install with dev dependencies
uv run pytest                                    # run all tests
uv run pytest --cov=brightspace_extractor        # run with coverage
uv run pytest -k "property"                      # property-based tests only
uv run pytest -m "not docker"                    # skip Docker integration tests
```

## Error Handling

- Setup errors (connection, auth, class not found, bad config) → fail fast with exit code 1
- Per-item errors (missing assignment, timeout, missing rubric) → log warning, skip, continue
- API errors → structured JSON `{"detail": "..."}` with appropriate HTTP status codes (422, 404, 500, 503)

## License

MIT — see [LICENSE](LICENSE).
