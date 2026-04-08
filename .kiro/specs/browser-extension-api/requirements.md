# Requirements Document

## Introduction

The Brightspace Feedback Extractor currently operates as a CLI tool that connects to a local browser via Chrome DevTools Protocol (CDP) to scrape Brightspace pages. This feature evolves the tool into a web service architecture: a FastAPI backend receives raw HTML from a Manifest V3 browser extension, parses it using the existing extraction functions, and returns structured JSON or PDF/markdown results. The extension solves the authentication problem — Brightspace uses SSO/2FA, so the backend cannot authenticate on behalf of users. Instead, the extension reads pages the user is already authenticated on and sends the HTML to the API. The existing CLI continues to work for local use.

The implementation spans four phases: (1) FastAPI layer wrapping existing extraction functions, (2) extraction adapter replacing Playwright locators with BeautifulSoup for static HTML parsing, (3) browser extension with content script and popup UI, and (4) Docker deployment on a Hetzner VPS.

## Glossary

- **API**: The FastAPI backend application that receives HTML and returns extracted data as JSON or PDF.
- **Extension**: The Manifest V3 Chrome/Edge browser extension that captures page HTML and communicates with the API.
- **Content_Script**: The extension component injected into Brightspace pages that reads the DOM.
- **Popup_UI**: The extension's popup or sidebar interface where users trigger extraction and view results.
- **Extraction_Adapter**: A thin wrapper that exposes Playwright-compatible `.locator()`, `.count()`, `.text_content()`, `.get_attribute()` methods backed by BeautifulSoup, allowing extraction functions to work on static HTML without code changes.
- **Page_Type**: A string identifier derived from the Brightspace URL pattern that determines which extraction function to invoke (e.g. `classlist`, `assignments`, `groups`, `quizzes`, `rubrics`, `submissions`).
- **Extraction_Functions**: The existing pure-ish functions in `extraction.py` that scrape structured data from Brightspace pages: `extract_courses`, `extract_assignments`, `extract_classlist`, `extract_groups`, `extract_quizzes`, `extract_rubrics`, `extract_group_submissions`.
- **CLI**: The existing cyclopts-based command-line interface that connects to a local browser via CDP.

## Requirements

### Requirement 1: API Listing Endpoints

**User Story:** As a user of the browser extension, I want to send Brightspace page HTML to the API and receive structured JSON, so that I can view classlist, assignments, groups, quizzes, and rubrics data without running the CLI locally.

#### Acceptance Criteria

1. WHEN the API receives a POST request to `/api/classlist` containing valid Brightspace classlist HTML in the request body, THE API SHALL return a JSON array of objects each containing `name`, `org_defined_id`, and `role` fields.
2. WHEN the API receives a POST request to `/api/assignments` containing valid Brightspace dropbox list HTML in the request body, THE API SHALL return a JSON array of objects each containing `assignment_id` and `name` fields.
3. WHEN the API receives a POST request to `/api/groups` containing valid Brightspace groups HTML in the request body, THE API SHALL return a JSON array of objects each containing `group_name`, `category`, and `members` fields.
4. WHEN the API receives a POST request to `/api/quizzes` containing valid Brightspace quizzes HTML in the request body, THE API SHALL return a JSON array of objects each containing `quiz_id` and `name` fields.
5. WHEN the API receives a POST request to `/api/rubrics` containing valid Brightspace rubrics HTML in the request body, THE API SHALL return a JSON array of objects each containing `rubric_id`, `name`, `rubric_type`, `scoring_method`, and `status` fields.
6. WHEN the API receives a POST request with an empty or missing HTML body, THE API SHALL return HTTP 422 with a JSON error object containing a descriptive `detail` field.

### Requirement 2: API Extract Endpoint

**User Story:** As a user of the browser extension, I want to send assignment submission page HTML to the API and receive rubric feedback as markdown or PDF, so that I can download formatted feedback reports directly from the browser.

#### Acceptance Criteria

1. WHEN the API receives a POST request to `/api/extract` containing valid Brightspace submission page HTML, THE API SHALL parse the HTML into GroupSubmission models using the existing parsing pipeline and return the result as a markdown string with content type `text/markdown`.
2. WHEN the API receives a POST request to `/api/extract` with the query parameter `format=pdf`, THE API SHALL return the extracted feedback as a PDF file with content type `application/pdf`.
3. WHEN the API receives a POST request to `/api/extract` with the query parameter `format=json`, THE API SHALL return the extracted feedback as a JSON array of serialized GroupSubmission objects.
4. WHEN the API receives a POST request to `/api/extract` containing HTML that yields zero parseable group submissions, THE API SHALL return HTTP 404 with a JSON error object containing a descriptive `detail` field.
5. WHEN the API receives a POST request to `/api/extract` with an optional `category` query parameter and a valid `category_config` is available, THE API SHALL filter rubric criteria by the specified category before serialization.

### Requirement 3: Extraction Adapter

**User Story:** As a developer, I want the existing extraction functions to work on static HTML strings without Playwright, so that the API can reuse the proven extraction logic without code duplication.

#### Acceptance Criteria

1. THE Extraction_Adapter SHALL expose a `.locator(selector)` method that accepts CSS selectors and returns an object supporting `.count()`, `.text_content()`, `.get_attribute(name)`, `.nth(index)`, `.first`, and `.filter()` methods, matching the Playwright Locator interface used by the Extraction_Functions.
2. THE Extraction_Adapter SHALL accept a raw HTML string and parse it using BeautifulSoup.
3. WHEN an Extraction_Function is called with the Extraction_Adapter instead of a Playwright Page, THE Extraction_Function SHALL produce identical output for the same HTML content.
4. FOR ALL valid HTML fixture files in the test suite, parsing with the Extraction_Adapter then extracting SHALL produce the same results as loading the fixture in Playwright then extracting (round-trip equivalence property).
5. THE Extraction_Adapter SHALL support the `wait_for_selector`, `wait_for_load_state`, and `wait_for_timeout` methods as no-ops, so that Extraction_Functions that call these methods do not raise errors when used with static HTML.
6. THE CLI SHALL continue to use Playwright for browser-based extraction without modification.

### Requirement 4: API Statelessness and Configuration

**User Story:** As a developer deploying the API, I want the API to be stateless and configurable via environment variables, so that it follows 12-factor principles and runs reliably in Docker.

#### Acceptance Criteria

1. THE API SHALL maintain no session state between requests — each request SHALL be processed independently using only the data in the request body and query parameters.
2. THE API SHALL read configuration values (base URL, category config path, pandoc path) from environment variables with the `BRIGHTSPACE_` prefix, consistent with the existing CLI configuration precedence.
3. WHEN the API starts, THE API SHALL expose a `GET /health` endpoint that returns HTTP 200 with a JSON body containing `{"status": "ok"}`.
4. THE API SHALL include CORS headers allowing requests from browser extensions (origin `chrome-extension://*` and `moz-extension://*`).

### Requirement 5: Browser Extension — Page Capture

**User Story:** As a Brightspace user, I want the browser extension to capture the HTML of the Brightspace page I am viewing, so that I can send it to the API for extraction without any manual copy-paste.

#### Acceptance Criteria

1. WHEN the user clicks the extension toolbar button while on a Brightspace page, THE Extension SHALL read `document.documentElement.outerHTML` from the active tab via the Content_Script.
2. THE Extension SHALL detect the Page_Type from the current tab URL by matching against known Brightspace URL patterns (`classlist.d2l`, `folders_manage.d2l`, `group_list.d2l`, `quizzes_manage.d2l`, `rubrics/list.d2l`, `folder_submissions_users.d2l`).
3. WHEN the current tab URL does not match any known Brightspace URL pattern, THE Popup_UI SHALL display a message indicating the current page is not a supported Brightspace page.
4. THE Extension SHALL use Manifest V3 with the minimum required permissions: `activeTab`, `scripting`, and `storage`.
5. WHEN the Content_Script fails to read the page HTML (e.g. due to a cross-origin frame), THE Extension SHALL display an error message in the Popup_UI describing the failure.

### Requirement 6: Browser Extension — API Communication

**User Story:** As a Brightspace user, I want the extension to send captured HTML to the API and display the results, so that I can extract data without leaving the browser.

#### Acceptance Criteria

1. WHEN the Extension has captured page HTML and detected a listing Page_Type, THE Extension SHALL send a POST request to the corresponding API listing endpoint with the HTML as the request body.
2. WHEN the Extension has captured page HTML and detected a submissions Page_Type, THE Extension SHALL send a POST request to `/api/extract` with the HTML as the request body.
3. WHEN the API returns a JSON response for a listing endpoint, THE Popup_UI SHALL render the data as a formatted table.
4. WHEN the API returns a PDF response for an extract endpoint, THE Popup_UI SHALL offer the PDF as a downloadable file.
5. WHEN the API returns an error response (HTTP 4xx or 5xx), THE Popup_UI SHALL display the error detail message from the JSON response body.
6. THE Extension SHALL read the API base URL from extension storage, defaulting to a configurable value set during installation.
7. WHILE the Extension is waiting for an API response, THE Popup_UI SHALL display a loading indicator.

### Requirement 7: Browser Extension — Popup UI

**User Story:** As a Brightspace user, I want a clean popup interface that shows me what data can be extracted from the current page and lets me trigger extraction with one click.

#### Acceptance Criteria

1. WHEN the user opens the Popup_UI on a supported Brightspace page, THE Popup_UI SHALL display the detected Page_Type and an "Extract" button.
2. WHEN the user opens the Popup_UI on a submissions page, THE Popup_UI SHALL display options to choose the output format (JSON, markdown, or PDF).
3. WHEN extraction results are displayed as a table, THE Popup_UI SHALL allow the user to copy the table data to the clipboard as tab-separated values.
4. THE Popup_UI SHALL include a settings view where the user can configure the API base URL.
5. WHEN the Popup_UI displays extraction results, THE Popup_UI SHALL show the count of extracted items (e.g. "37 students found").

### Requirement 8: Docker Deployment

**User Story:** As a developer, I want to deploy the API as a Docker container on a VPS, so that the extension can reach it over HTTPS without requiring users to run Python locally.

#### Acceptance Criteria

1. THE API SHALL be packaged as a Docker image based on `python:3.14-slim` with `pandoc` installed for PDF export.
2. THE Docker image SHALL use `uvicorn` to serve the FastAPI application on port 8000.
3. THE Docker image SHALL install dependencies using `uv sync --no-dev` to exclude development dependencies.
4. WHEN the Docker container starts, THE API SHALL be reachable at the configured port and respond to `GET /health` within 5 seconds.
5. THE deployment SHALL include a `docker-compose.yml` file that defines the API service with health check, restart policy, and environment variable configuration.

### Requirement 9: API Error Handling

**User Story:** As a user of the browser extension, I want clear error messages when extraction fails, so that I can understand what went wrong and take corrective action.

#### Acceptance Criteria

1. WHEN the API receives HTML that cannot be parsed by the Extraction_Adapter (e.g. malformed HTML), THE API SHALL return HTTP 422 with a JSON error object containing a descriptive `detail` field.
2. WHEN an Extraction_Function raises an exception during processing, THE API SHALL return HTTP 500 with a JSON error object containing a generic error message that does not expose internal stack traces.
3. WHEN the API receives a request to `/api/extract` with `format=pdf` and pandoc is not available, THE API SHALL return HTTP 503 with a JSON error object indicating that PDF export is temporarily unavailable.
4. THE API SHALL log all errors with sufficient context (endpoint, Page_Type, error message) for debugging, using Python's standard logging module.

### Requirement 10: Backward Compatibility

**User Story:** As an existing CLI user, I want the CLI to continue working exactly as before, so that the new API and extension do not break my local workflow.

#### Acceptance Criteria

1. THE CLI SHALL continue to connect to a local browser via CDP and extract data using Playwright, with no changes to command syntax or behavior.
2. THE CLI SHALL continue to support all existing flags (`--config`, `--cdp-url`, `--base-url`, `--output-dir`, `--category`, `--pdf`, `--combined`, `--col-widths`).
3. THE existing 192 tests SHALL continue to pass without modification after the Extraction_Adapter and API are added.
4. THE Extraction_Functions SHALL remain callable with both a Playwright Page object and the Extraction_Adapter, determined by the caller (CLI uses Playwright, API uses Extraction_Adapter).
