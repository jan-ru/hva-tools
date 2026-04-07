"""CLI entry point and pipeline orchestration using cyclopts."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Annotated

import cyclopts

from brightspace_extractor.aggregation import aggregate_by_group
from brightspace_extractor.browser import connect_to_browser, verify_authentication
from brightspace_extractor.exceptions import (
    AuthenticationError,
    ConfigError,
    ConnectionError,
    NavigationError,
    PdfExportError,
)
from brightspace_extractor.extraction import extract_group_submissions
from brightspace_extractor.filtering import (
    filter_assignment_feedback,
    get_patterns,
    load_category_config,
)
from brightspace_extractor.navigation import (
    navigate_to_assignment_submissions,
    navigate_to_class,
)
from brightspace_extractor.parsing import parse_all_submissions
from brightspace_extractor.pdf_export import check_pandoc_available, export_all_pdfs
from brightspace_extractor.serialization import (
    group_to_filename,
    render_group_markdown_pandoc,
    write_feedback_files,
)

logger = logging.getLogger(__name__)

app = cyclopts.App(
    name="brightspace-extractor", help="Extract rubric feedback from Brightspace DLO."
)


def _fail_fast(exc: Exception, browser=None) -> None:
    """Log an error and exit. Optionally close the browser first."""
    logger.error("%s", exc)
    if browser is not None:
        browser.close()
    sys.exit(1)


def _parse_col_widths(raw: str) -> tuple[int, int, int]:
    """Parse a comma-separated string of three positive integers.

    Raises ValueError with a descriptive message on invalid input.
    """
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 3:
        raise ValueError(
            f"--col-widths must be exactly three comma-separated positive integers (e.g., 3,1,6), got {len(parts)} values"
        )
    values: list[int] = []
    for p in parts:
        try:
            v = int(p)
        except ValueError:
            raise ValueError(
                f"--col-widths values must be positive integers, got '{p}'"
            ) from None
        if v <= 0:
            raise ValueError(f"--col-widths values must be positive integers, got {v}")
        values.append(v)
    return (values[0], values[1], values[2])


@app.command
def extract(
    class_id: Annotated[str, cyclopts.Parameter(help="Brightspace class identifier")],
    assignment_ids: Annotated[
        list[str], cyclopts.Parameter(help="One or more assignment identifiers")
    ],
    *,
    output_dir: Annotated[
        str, cyclopts.Parameter(help="Output directory for markdown files")
    ] = "./output",
    cdp_url: Annotated[
        str, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = "http://localhost:9222",
    base_url: Annotated[
        str, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = "https://dlo.mijnhva.nl",
    category: Annotated[
        str | None, cyclopts.Parameter(help="Category to filter criteria by")
    ] = None,
    category_config: Annotated[
        str | None, cyclopts.Parameter(help="Path to category TOML config file")
    ] = None,
    pdf: Annotated[
        bool, cyclopts.Parameter(help="Generate PDF output via pandoc + typst")
    ] = False,
    col_widths: Annotated[
        str | None,
        cyclopts.Parameter(
            help="Column width ratios as three comma-separated positive integers (e.g., 3,1,6)"
        ),
    ] = None,
) -> None:
    """Extract rubric feedback for specified class and assignments."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # --- validate new CLI parameters (fail-fast) ---
    if category and not category_config:
        logger.error("--category requires --category-config to be specified")
        sys.exit(1)

    # Parse col_widths early so we fail fast on bad input
    parsed_col_widths: tuple[int, int, int] = (3, 1, 6)
    if col_widths is not None:
        try:
            parsed_col_widths = _parse_col_widths(col_widths)
        except ValueError as exc:
            _fail_fast(exc)

    # Load category config and validate category name
    patterns: tuple[str, ...] | None = None
    if category:
        try:
            config = load_category_config(category_config)  # type: ignore[arg-type]
            patterns = get_patterns(config, category)
        except ConfigError as exc:
            _fail_fast(exc)

    # --- connect to browser (fail-fast) ---
    try:
        browser, _context, page = connect_to_browser(cdp_url)
    except ConnectionError as exc:
        _fail_fast(exc)

    # --- verify authentication (fail-fast) ---
    try:
        if not verify_authentication(page):
            raise AuthenticationError(
                "Browser session is not authenticated. Please log in to Brightspace manually."
            )
    except AuthenticationError as exc:
        _fail_fast(exc, browser)

    # --- navigate to class (fail-fast) ---
    try:
        navigate_to_class(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    # --- loop assignments: extract → parse (graceful degradation) ---
    all_feedbacks = []
    for assignment_id in assignment_ids:
        try:
            navigate_to_assignment_submissions(
                page, class_id, assignment_id, base_url=base_url
            )
        except NavigationError as exc:
            logger.warning("Skipping assignment %s: %s", assignment_id, exc)
            continue

        # Use assignment_id as the name; the extraction layer doesn't know the
        # human-readable name without extra navigation.
        assignment_name = assignment_id
        print(f"Processing assignment: {assignment_name}")

        raw_submissions = extract_group_submissions(page)
        for raw in raw_submissions:
            print(f"  Processing group: {raw.get('group_name', '<unknown>')}")

        feedbacks = parse_all_submissions(
            raw_submissions, assignment_name, assignment_id
        )
        all_feedbacks.extend(feedbacks)

    # --- filter (optional) → aggregate → serialize → write ---
    if patterns is not None:
        all_feedbacks = [
            filter_assignment_feedback(af, patterns) for af in all_feedbacks
        ]

    groups = aggregate_by_group(all_feedbacks)

    if pdf:
        # Write files manually using pandoc-compatible renderer
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for gf in groups:
            filename = group_to_filename(gf.group_name, suffix=category)
            md_content = render_group_markdown_pandoc(
                gf,
                col_widths=parsed_col_widths,
                category_label=category,
            )
            (out / filename).write_text(md_content, encoding="utf-8")

        # Convert to PDF
        try:
            check_pandoc_available()
        except PdfExportError as exc:
            _fail_fast(exc, browser)

        success, failure = export_all_pdfs(output_dir)
        print(
            f"\nDone. {len(groups)} group(s) processed. "
            f"PDF: {success} succeeded, {failure} failed. "
            f"Output written to: {output_dir}"
        )
    else:
        write_feedback_files(groups, output_dir)
        print(
            f"\nDone. {len(groups)} group(s) processed. Output written to: {output_dir}"
        )

    browser.close()
