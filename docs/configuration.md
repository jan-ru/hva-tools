# Configuration

## Config Files

Store shared parameters in TOML config files under the `config/` directory. The tool auto-loads `config/brightspace.toml` for shared defaults (base URL, CDP endpoint). Create per-course configs for course-specific settings:

```
config/
├── brightspace.toml          # shared defaults (auto-loaded)
├── brightspace.example.toml  # template (committed to git)
├── Data&Control.toml         # course-specific
├── BigData.toml
└── GRC.toml
```

Example course config (`config/Data&Control.toml`):

```toml
class_id = "698557"
output_dir = "./output/data&control"
category_config = "categories.toml"
```

Use `--config` to select a course:

```bash
brightspace-extractor classlist --config "config/Data&Control.toml"
brightspace-extractor assignments --config config/BigData.toml
```

Without `--config`, only `config/brightspace.toml` is loaded (shared defaults). CLI arguments always override config values.

Supported keys: `class_id`, `base_url`, `cdp_url`, `output_dir`, `category_config`, `pandoc_path`.

### `pandoc_path`

Override the path to the `pandoc` binary. Useful when pandoc is not on your system `PATH` (e.g., installed via scoop):

```toml
pandoc_path = "C:\\Users\\you\\scoop\\apps\\pandoc\\3.9\\pandoc.exe"
```

Defaults to `"pandoc"` (i.e., looked up from `PATH`).

## Environment Variables

All config keys can also be set via environment variables with a `BRIGHTSPACE_` prefix:

| Variable | Equivalent config key |
|---|---|
| `BRIGHTSPACE_CLASS_ID` | `class_id` |
| `BRIGHTSPACE_BASE_URL` | `base_url` |
| `BRIGHTSPACE_CDP_URL` | `cdp_url` |
| `BRIGHTSPACE_OUTPUT_DIR` | `output_dir` |
| `BRIGHTSPACE_CATEGORY_CONFIG` | `category_config` |

## Resolution Order

Parameters are resolved with the following precedence (first match wins):

1. CLI flag (e.g. `--cdp-url http://localhost:5555`)
2. Environment variable (e.g. `BRIGHTSPACE_CDP_URL=http://localhost:5555`)
3. Config file value (from `--config` or `config/brightspace.toml`)
4. Built-in default

## Category Filtering

Filter rubric criteria by category using a TOML config file. Each category maps to a list of substring patterns matched case-insensitively against criterion names:

```toml
[categories]
MIS = ["informatie behoefte", "Dashboard", "Cloud"]
MAC = ["kostprijs", "budget omzet"]
```

Use `--category MIS --category-config categories.toml` to include only criteria matching the MIS patterns. The `category_config` key can also be set in a config file to avoid repeating it.

## Docker Deployment (API)

The API runs in Docker and reads configuration from environment variables only (no config files needed).

### Quick Start

```bash
docker compose up -d
```

The API is available at `http://localhost:8000`. Verify with:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Environment Variables

Set in `docker-compose.yml` or via `docker run -e`:

| Variable | Default | Description |
|---|---|---|
| `BRIGHTSPACE_BASE_URL` | `https://dlo.mijnhva.nl` | Brightspace instance base URL |
| `BRIGHTSPACE_CATEGORY_CONFIG` | — | Path to category TOML inside the container (e.g. `/app/categories.toml`) |
| `BRIGHTSPACE_ASSIGNMENT_NAME` | `Assignment` | Default assignment name for extract endpoint |
| `BRIGHTSPACE_ASSIGNMENT_ID` | `0` | Default assignment ID for extract endpoint |

### Docker Compose

The included `docker-compose.yml` defines the API service with:

- Port mapping: `8000:8000`
- Health check: polls `/health` every 30s (5s timeout, 3 retries, 5s start period)
- Restart policy: `unless-stopped`
- Pandoc pre-installed for PDF export

### Dockerfile

Base image: `python:3.14-slim`. Dependencies installed with `uv sync --no-dev --frozen`. Pandoc installed via apt for PDF export. Runs uvicorn on port 8000.

## Browser Extension Settings

The extension stores its configuration in `chrome.storage.local`:

| Setting | Default | Description |
|---|---|---|
| API base URL | `http://localhost:8000` | The URL of the FastAPI backend |

Configure via the extension's options page (right-click extension icon → Options).
