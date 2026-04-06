"""CLI entry point and pipeline orchestration using cyclopts."""

from __future__ import annotations

import logging
import sys
from typing import Annotated

import cyclopts

from brightspace_extractor.aggregation import aggregate_by_group
from brightspace_extractor.browser import connect_to_browser, verify_authentication
from brightspace_extractor.exceptions import (
    AuthenticationError,
    ConnectionError,
    NavigationError,
)
from brightspace_extractor.extraction import extract_group_submissions
from brightspace_extractor.navigation import (
    navigate_to_assignment_submissions,
    navigate_to_class,
)
from brightspace_extractor.parsing import parse_all_submissions
from brightspace_extractor.serialization import write_feedback_files

logger = logging.getLogger(__name__)

app = cyclopts.App(
    name="brightspace-extractor", help="Extract rubric feedback from Brightspace DLO."
)


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
) -> None:
    """Extract rubric feedback for specified class and assignments."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # --- connect to browser (fail-fast) ---
    try:
        browser, _context, page = connect_to_browser(cdp_url)
    except ConnectionError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    # --- verify authentication (fail-fast) ---
    try:
        if not verify_authentication(page):
            raise AuthenticationError(
                "Browser session is not authenticated. Please log in to Brightspace manually."
            )
    except AuthenticationError as exc:
        logger.error("%s", exc)
        browser.close()
        sys.exit(1)

    # --- navigate to class (fail-fast) ---
    try:
        navigate_to_class(page, class_id)
    except NavigationError as exc:
        logger.error("%s", exc)
        browser.close()
        sys.exit(1)

    # --- loop assignments: extract → parse (graceful degradation) ---
    all_feedbacks = []
    for assignment_id in assignment_ids:
        try:
            navigate_to_assignment_submissions(page, class_id, assignment_id)
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

    # --- aggregate → serialize → write ---
    groups = aggregate_by_group(all_feedbacks)
    write_feedback_files(groups, output_dir)

    print(f"\nDone. {len(groups)} group(s) processed. Output written to: {output_dir}")
    browser.close()
