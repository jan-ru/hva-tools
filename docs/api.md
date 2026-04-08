# API Endpoints

The FastAPI backend receives raw HTML from the browser extension and returns structured data. All listing endpoints accept HTML as the raw request body (`Content-Type: text/html`).

Base URL: `http://localhost:8000` (configurable via Docker or extension settings).

## Health

```
GET /health
```

Returns `{"status": "ok"}` with HTTP 200. Used by Docker health checks.

## Listing Endpoints

Each endpoint accepts a POST with Brightspace page HTML in the body and returns a JSON array.

### Classlist

```
POST /api/classlist
Content-Type: text/html

<html>...brightspace classlist page...</html>
```

Response: `[{"name": "...", "org_defined_id": "...", "role": "..."}]`

### Assignments

```
POST /api/assignments
Content-Type: text/html
```

Response: `[{"assignment_id": "...", "name": "..."}]`

### Groups

```
POST /api/groups
Content-Type: text/html
```

Response: `[{"group_name": "...", "category": "...", "members": "..."}]`

### Quizzes

```
POST /api/quizzes
Content-Type: text/html
```

Response: `[{"quiz_id": "...", "name": "..."}]`

### Rubrics

```
POST /api/rubrics
Content-Type: text/html
```

Response: `[{"rubric_id": "...", "name": "...", "type": "...", "scoring_method": "...", "status": "..."}]`

## Extract Endpoint

```
POST /api/extract?format=markdown&category=MIS
Content-Type: text/html
```

Query parameters:

| Parameter | Default | Values | Description |
|---|---|---|---|
| `format` | `markdown` | `markdown`, `pdf`, `json` | Output format |
| `category` | — | Category name | Filter criteria by category (requires `BRIGHTSPACE_CATEGORY_CONFIG`) |

Response by format:

| Format | Content-Type | Description |
|---|---|---|
| `markdown` | `text/markdown` | Rendered markdown string |
| `pdf` | `application/pdf` | PDF file (requires pandoc) |
| `json` | `application/json` | Serialized GroupFeedback objects |

## Error Responses

All errors return JSON with a `detail` field:

```json
{"detail": "Human-readable error description"}
```

| Status | Condition |
|---|---|
| 422 | Empty or missing HTML body |
| 422 | Invalid `format` parameter |
| 422 | Invalid `category` or missing category config |
| 404 | No submissions found in HTML |
| 500 | Internal extraction error (details logged server-side) |
| 503 | PDF export unavailable (pandoc not found) |

## CORS

The API allows requests from browser extensions:
- `chrome-extension://*`
- `moz-extension://*`

Methods: `GET`, `POST`. All headers allowed.
