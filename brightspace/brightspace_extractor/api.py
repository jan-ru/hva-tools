"""FastAPI application for the Brightspace Feedback Extractor.

Receives raw HTML from the browser extension, parses it using the
:class:`~brightspace_extractor.adapter.ExtractionAdapter`, and returns
structured JSON, markdown, or PDF via the existing extraction pipeline.
"""

from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from brightspace_extractor.adapter import ExtractionAdapter
from brightspace_extractor.aggregation import aggregate_by_group
from brightspace_extractor.exceptions import ConfigError, PdfExportError
from brightspace_extractor.extraction import (
    extract_assignments,
    extract_classlist,
    extract_groups,
    extract_quizzes,
    extract_rubrics,
)
from brightspace_extractor.filtering import (
    filter_assignment_feedback,
    get_patterns,
    load_category_config,
)
from brightspace_extractor.parsing import parse_all_submissions
from brightspace_extractor.pdf_export import check_pandoc_available, convert_md_to_pdf
from brightspace_extractor.serialization import render_group_markdown

logger = logging.getLogger(__name__)

app = FastAPI(title="Brightspace Feedback Extractor API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome|moz)-extension://.*$",
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Maximum request body size: 10 MB. Brightspace pages are typically 1-3 MB.
MAX_BODY_BYTES = 10 * 1024 * 1024


async def _read_html(request: Request) -> str:
    """Read and validate the raw HTML body from the request."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Request body too large (max {MAX_BODY_BYTES // 1024 // 1024} MB)",
        )

    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Request body too large (max {MAX_BODY_BYTES // 1024 // 1024} MB)",
        )

    html = body.decode("utf-8", errors="replace").strip()
    if not html:
        raise HTTPException(
            status_code=422,
            detail="Request body must contain non-empty HTML",
        )
    return html


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Listing endpoints (generated from registry to avoid repetition)
# ---------------------------------------------------------------------------

LISTING_ENDPOINTS: dict[str, Callable] = {
    "classlist": extract_classlist,
    "assignments": extract_assignments,
    "groups": extract_groups,
    "quizzes": extract_quizzes,
    "rubrics": extract_rubrics,
}


def _make_listing_endpoint(name: str, extract_fn: Callable):
    """Create a POST endpoint for a listing extraction function."""

    async def _endpoint(request: Request) -> list[dict]:
        html = await _read_html(request)
        try:
            return extract_fn(ExtractionAdapter(html))
        except Exception:
            logger.exception("Error extracting %s", name)
            raise HTTPException(status_code=500, detail="Internal extraction error")

    _endpoint.__name__ = f"api_{name}"
    _endpoint.__qualname__ = f"api_{name}"
    return _endpoint


for _name, _fn in LISTING_ENDPOINTS.items():
    app.post(f"/api/{_name}")(_make_listing_endpoint(_name, _fn))


# ---------------------------------------------------------------------------
# Extract endpoint
# ---------------------------------------------------------------------------


@app.post("/api/extract")
async def api_extract(
    request: Request,
    output_format: str = Query(
        "markdown", alias="format", pattern=r"^(markdown|pdf|json)$"
    ),
    category: str | None = Query(None),
) -> Response:
    html = await _read_html(request)

    try:
        adapter = ExtractionAdapter(html)
        raw_submissions = _extract_static_submissions(adapter)
    except Exception:
        logger.exception("Error extracting submissions")
        raise HTTPException(status_code=500, detail="Internal extraction error")

    if not raw_submissions:
        raise HTTPException(
            status_code=404,
            detail="No group submissions found in the provided HTML",
        )

    feedbacks = parse_all_submissions(
        raw_submissions,
        assignment_name=os.environ.get("BRIGHTSPACE_ASSIGNMENT_NAME", "Assignment"),
        assignment_id=os.environ.get("BRIGHTSPACE_ASSIGNMENT_ID", "0"),
    )

    if not feedbacks:
        raise HTTPException(
            status_code=404,
            detail="No group submissions found in the provided HTML",
        )

    # Apply category filtering if requested
    if category:
        config_path = os.environ.get("BRIGHTSPACE_CATEGORY_CONFIG", "")
        if not config_path:
            raise HTTPException(
                status_code=422,
                detail="Category filtering requested but BRIGHTSPACE_CATEGORY_CONFIG not set",
            )
        try:
            config = load_category_config(config_path)
            patterns = get_patterns(config, category)
        except ConfigError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        feedbacks = [filter_assignment_feedback(f, patterns) for f in feedbacks]

    # Aggregate and serialize
    groups = aggregate_by_group(feedbacks)

    if output_format == "json":
        return JSONResponse([g.model_dump() for g in groups])

    # Render markdown
    md_parts = [render_group_markdown(g) for g in groups]
    md_text = "\n\n".join(md_parts)

    if output_format == "markdown":
        return Response(content=md_text, media_type="text/markdown")

    # PDF
    try:
        check_pandoc_available()
    except PdfExportError:
        raise HTTPException(
            status_code=503,
            detail="PDF export temporarily unavailable (pandoc not found)",
        )

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = str(Path(tmpdir) / "output.md")
            pdf_path = str(Path(tmpdir) / "output.pdf")
            Path(md_path).write_text(md_text, encoding="utf-8")
            convert_md_to_pdf(md_path, pdf_path)
            pdf_bytes = Path(pdf_path).read_bytes()
        return Response(content=pdf_bytes, media_type="application/pdf")
    except PdfExportError as exc:
        logger.error("PDF conversion failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="PDF export temporarily unavailable",
        )


def _extract_static_submissions(adapter: ExtractionAdapter) -> list[dict]:
    """Extract group submission dicts from static submission page HTML.

    This is the API-path equivalent of extract_group_submissions, but works
    on static HTML without Playwright navigation. It finds group rows and
    extracts whatever rubric data is visible in the pre-rendered page.

    Limitations (MVP):
        Only group names are extracted from the submission list page. Student
        lists, rubric criteria, and submission dates require navigating into
        each group's evaluation page, which is not possible with static HTML.
        The returned dicts have empty ``students``, ``rubric.criteria``, and
        ``submission_date`` fields.
    """
    submissions: list[dict] = []

    rows = adapter.locator("tr.d_ggl2")
    row_count = rows.count()

    for i in range(row_count):
        row = rows.nth(i)

        # Group name from eval link title
        link = row.locator("a[title^='Go to Evaluation for ']")
        if link.count() == 0:
            continue
        title = link.first.get_attribute("title") or ""
        group_name = title.removeprefix("Go to Evaluation for ").strip()
        if not group_name:
            continue

        submissions.append(
            {
                "group_name": group_name,
                "students": [],
                "rubric": {"criteria": []},
                "submission_date": "",
            }
        )

    return submissions
