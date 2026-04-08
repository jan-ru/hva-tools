# Implementation Plan: Browser Extension + API

## Overview

Transform the Brightspace Feedback Extractor from CLI-only into a dual-interface system by adding a FastAPI backend, a BeautifulSoup-backed extraction adapter, a Manifest V3 browser extension, and Docker deployment. Implementation follows the design's four phases: adapter first (foundation), then API layer, browser extension, and finally Docker packaging. All 192 existing tests must continue to pass throughout.

## Tasks

- [x] 1. Implement Extraction Adapter (`brightspace_extractor/adapter.py`)
  - [x] 1.1 Create `SoupLocator` class with BeautifulSoup-backed Playwright Locator interface
    - Implement `__init__`, `count`, `nth`, `first`, `text_content`, `get_attribute`, `locator`, `filter`, `wait_for` (no-op), `select_option` (no-op)
    - CSS selector delegation via `BeautifulSoup.select()`
    - `filter(has=...)` must check if child elements match the sub-selector
    - _Requirements: 3.1, 3.5_

  - [x] 1.2 Create `ExtractionAdapter` class as drop-in replacement for Playwright `Page`
    - Implement `__init__` (accepts HTML string, parses with BeautifulSoup), `locator`, `wait_for_selector` (no-op), `wait_for_load_state` (no-op), `wait_for_timeout` (no-op), `url` property
    - _Requirements: 3.2, 3.5, 3.6_

  - [x] 1.3 Validate adapter against all HTML fixture files
    - Load each fixture (`classlist-debug.html`, `assignments-debug.html`, `groups-debug.html`, `quizzes-debug.html`, `rubrics-debug.html`) with `ExtractionAdapter`
    - Call the corresponding extraction function and verify output matches the existing Playwright-based fixture test expectations
    - _Requirements: 3.3, 3.4, 10.3, 10.4_

  - [x] 1.4 Write property test: Adapter–Playwright Extraction Equivalence (Property 1)
    - **Property 1: Adapter–Playwright Extraction Equivalence**
    - Parameterize over all HTML fixture files; for each, load in both Playwright and the adapter, run the extraction function, compare outputs
    - **Validates: Requirements 3.3, 3.4, 10.4**

  - [x] 1.5 Write property test: Listing Extraction Structural Correctness (Property 2)
    - **Property 2: Listing Extraction Structural Correctness**
    - Generate random Brightspace-structured HTML using Hypothesis strategies, extract via adapter, verify output structure (correct keys, non-empty values, count matches DOM elements)
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

- [x] 2. Checkpoint — Adapter complete
  - Ensure all tests pass (existing 192 + new adapter tests), ask the user if questions arise.

- [x] 3. Implement FastAPI Application (`brightspace_extractor/api.py`)
  - [x] 3.1 Add `fastapi`, `uvicorn`, `beautifulsoup4` dependencies to `pyproject.toml`
    - Run `uv add fastapi uvicorn beautifulsoup4`
    - _Requirements: 4.1, 4.2_

  - [x] 3.2 Create FastAPI app with CORS middleware and health endpoint
    - Configure `CORSMiddleware` allowing `chrome-extension://` and `moz-extension://` origins
    - Implement `GET /health` returning `{"status": "ok"}`
    - _Requirements: 4.3, 4.4_

  - [x] 3.3 Implement listing endpoints (`/api/classlist`, `/api/assignments`, `/api/groups`, `/api/quizzes`, `/api/rubrics`)
    - Each endpoint reads raw HTML from request body (`Content-Type: text/html`)
    - Validates non-empty body (HTTP 422 on empty)
    - Creates `ExtractionAdapter` from HTML, calls corresponding extraction function, returns JSON array
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 3.4 Implement extract endpoint (`/api/extract`)
    - Accept `format` query param (`markdown`, `pdf`, `json`) and optional `category` query param
    - Parse HTML via adapter, run through parsing pipeline (`parse_all_submissions`), apply category filtering if specified
    - Return markdown (`text/markdown`), PDF (`application/pdf`), or JSON based on format param
    - Handle error cases: no submissions (404), pandoc unavailable for PDF (503), invalid format/category (422)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.5 Implement API error handling
    - Return structured `{"detail": "..."}` JSON for all error responses
    - Log errors with context (endpoint, error message) using Python logging
    - Never expose stack traces in responses
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 3.6 Write unit tests for API endpoints using FastAPI TestClient
    - Test each listing endpoint with known HTML fixtures, verify JSON response structure
    - Test health endpoint returns 200 with correct body
    - Test CORS headers for extension origins
    - Test error responses: empty body (422), no submissions (404), bad format param (422)
    - _Requirements: 1.1–1.6, 2.1–2.5, 4.3, 4.4, 9.1–9.4_

- [x] 4. Checkpoint — API complete
  - Ensure all tests pass (existing 192 + adapter + API tests), ask the user if questions arise.

- [x] 5. Implement Browser Extension (`extension/`)
  - [x] 5.1 Create `extension/manifest.json` with Manifest V3 configuration
    - Set permissions to `activeTab` and `scripting` only
    - Configure popup action, options page, and icons
    - _Requirements: 5.4_

  - [x] 5.2 Create `extension/content.js` — content script for HTML capture
    - Read `document.documentElement.outerHTML` and return it to the popup
    - Use `chrome.scripting.executeScript` with `activeTab` permission
    - _Requirements: 5.1, 5.5_

  - [x] 5.3 Create `extension/popup.html` and `extension/popup.js` — popup UI and logic
    - Detect page type from URL using `PAGE_PATTERNS` regex map
    - Display detected page type and "Extract" button on supported pages
    - Display "unsupported page" message on non-Brightspace pages
    - Show format selector (JSON/markdown/PDF) on submissions pages
    - Send captured HTML to appropriate API endpoint
    - Render listing results as table, offer PDF as download
    - Display item count (e.g. "37 students found")
    - Show loading indicator while waiting for API response
    - Display error messages from API error responses
    - Implement copy-to-clipboard as tab-separated values for table data
    - _Requirements: 5.2, 5.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 7.1, 7.2, 7.3, 7.5_

  - [x] 5.4 Create `extension/options.html` and `extension/options.js` — settings page
    - Allow user to configure API base URL, stored in `chrome.storage.local`
    - Default to configurable fallback URL
    - _Requirements: 6.6, 7.4_

  - [x] 5.5 Write property test: URL Pattern Detection (Property 3)
    - **Property 3: URL Pattern Detection**
    - Generate random URLs from known Brightspace patterns with random class IDs and query params, verify correct page type detection
    - Generate random non-Brightspace URLs, verify `None` returned
    - **Validates: Requirements 5.2, 5.3**

  - [x] 5.6 Write property test: Table-to-TSV Conversion (Property 4)
    - **Property 4: Table-to-TSV Conversion Preserves Content**
    - Generate random lists of dicts with string values, convert to TSV, verify line count, field count, and content preservation
    - **Validates: Requirements 7.3**

- [x] 6. Checkpoint — Extension complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Docker Deployment
  - [x] 7.1 Create `Dockerfile`
    - Base image `python:3.14-slim`, install `pandoc`, copy project, `uv sync --no-dev`, expose port 8000, run uvicorn
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 7.2 Create `docker-compose.yml`
    - Define API service with port mapping, environment variables (`BRIGHTSPACE_BASE_URL`, `BRIGHTSPACE_CATEGORY_CONFIG`), health check, restart policy
    - _Requirements: 8.4, 8.5_

  - [x] 7.3 Write integration test for Docker health check
    - Verify `/health` responds within 5 seconds after container start
    - _Requirements: 8.4_

- [x] 8. Final checkpoint — Ensure all tests pass
  - Ensure all existing 192 tests plus new tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The adapter (Phase 1) is the foundation — API and extension depend on it
- All extraction functions remain unchanged; only the adapter bridges BeautifulSoup to the Playwright Locator interface
- The CLI path is never modified — backward compatibility is maintained by design
- Property tests validate universal correctness properties from the design document
- Each task references specific requirement clauses for traceability
