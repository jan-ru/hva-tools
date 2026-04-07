"""CLI entry point and pipeline orchestration using cyclopts."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Annotated

import cyclopts
from playwright.sync_api import Browser, Page

from brightspace_extractor.aggregation import aggregate_by_group
from brightspace_extractor.browser import connect_to_browser, verify_authentication
from brightspace_extractor.exceptions import (
    AuthenticationError,
    ConfigError,
    ConnectionError,
    NavigationError,
    PdfExportError,
)
from brightspace_extractor.extraction import (
    extract_assignments,
    extract_classlist,
    extract_courses,
    extract_group_submissions,
    extract_groups,
)
from brightspace_extractor.filtering import (
    filter_assignment_feedback,
    get_patterns,
    load_category_config,
)
from brightspace_extractor.navigation import (
    navigate_to_assignment_submissions,
    navigate_to_class,
    navigate_to_classlist,
    navigate_to_dropbox_list,
    navigate_to_groups,
    navigate_to_home,
)
from brightspace_extractor.parsing import parse_all_submissions
from brightspace_extractor.pdf_export import (
    check_pandoc_available,
    export_all_pdfs,
    export_combined_pdf,
)
from brightspace_extractor.serialization import (
    group_to_filename,
    render_group_markdown_pandoc,
    write_feedback_files,
)

logger = logging.getLogger(__name__)

app = cyclopts.App(
    name="brightspace-extractor", help="Extract rubric feedback from Brightspace DLO."
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _fail_fast(exc: Exception, browser=None) -> None:
    """Log an error and exit. Optionally close the browser first."""
    logger.error("%s", exc)
    if browser is not None:
        browser.close()
    sys.exit(1)


def _connect_and_auth(
    cdp_url: str, base_url: str, class_id: str
) -> tuple[Browser, Page]:
    """Connect to browser, verify auth, navigate to class. Returns (browser, page).

    Calls sys.exit(1) on any failure.
    """
    try:
        browser, _context, page = connect_to_browser(cdp_url)
    except ConnectionError as exc:
        _fail_fast(exc)

    try:
        if not verify_authentication(page):
            raise AuthenticationError(
                "Browser session is not authenticated. "
                "Please log in to Brightspace manually."
            )
    except AuthenticationError as exc:
        _fail_fast(exc, browser)

    try:
        navigate_to_class(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    return browser, page  # type: ignore[return-value]


def _parse_col_widths(raw: str) -> tuple[int, int, int]:
    """Parse a comma-separated string of three positive integers.

    Raises ValueError with a descriptive message on invalid input.
    """
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 3:
        raise ValueError(
            f"--col-widths must be exactly three comma-separated positive integers "
            f"(e.g., 3,1,6), got {len(parts)} values"
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


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command
def courses(
    *,
    cdp_url: Annotated[
        str, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = "http://localhost:9222",
    base_url: Annotated[
        str, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = "https://dlo.mijnhva.nl",
    output_dir: Annotated[
        str | None, cyclopts.Parameter(help="Write a courses.md file to this directory")
    ] = None,
) -> None:
    """List enrolled courses (class IDs) from the Brightspace homepage."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        browser, _context, page = connect_to_browser(cdp_url)
    except ConnectionError as exc:
        _fail_fast(exc)

    try:
        if not verify_authentication(page):
            raise AuthenticationError(
                "Browser session is not authenticated. "
                "Please log in to Brightspace manually."
            )
    except AuthenticationError as exc:
        _fail_fast(exc, browser)

    try:
        navigate_to_home(page, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    items = extract_courses(page)
    browser.close()

    if not items:
        print("No courses found.")
        return

    print(f"\n{'Class ID':<12} Name")
    print(f"{'—' * 12} {'—' * 50}")
    for item in items:
        print(f"{item['class_id']:<12} {item['name']}")
    print(f"\n{len(items)} course(s) found.")

    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        lines = ["# Courses", "", "| Class ID | Name |", "|---|---|"]
        for item in items:
            lines.append(f"| {item['class_id']} | {item['name']} |")
        lines.append("")
        (out / "courses.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"Written to {out / 'courses.md'}")


@app.command
def assignments(
    class_id: Annotated[str, cyclopts.Parameter(help="Brightspace class identifier")],
    *,
    cdp_url: Annotated[
        str, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = "http://localhost:9222",
    base_url: Annotated[
        str, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = "https://dlo.mijnhva.nl",
) -> None:
    """List assignments (dropbox folders) for a class."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    browser, page = _connect_and_auth(cdp_url, base_url, class_id)

    try:
        navigate_to_dropbox_list(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    items = extract_assignments(page)
    browser.close()

    if not items:
        print("No assignments found.")
        return

    # Print as a simple table
    print(f"\n{'ID':<12} Name")
    print(f"{'—' * 12} {'—' * 40}")
    for item in items:
        print(f"{item['assignment_id']:<12} {item['name']}")
    print(f"\n{len(items)} assignment(s) found.")


@app.command
def classlist(
    class_id: Annotated[str, cyclopts.Parameter(help="Brightspace class identifier")],
    *,
    cdp_url: Annotated[
        str, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = "http://localhost:9222",
    base_url: Annotated[
        str, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = "https://dlo.mijnhva.nl",
    output_dir: Annotated[
        str | None,
        cyclopts.Parameter(help="Write a classlist.md file to this directory"),
    ] = None,
) -> None:
    """List students enrolled in a class."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    browser, page = _connect_and_auth(cdp_url, base_url, class_id)

    try:
        navigate_to_classlist(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    students = extract_classlist(page)
    browser.close()

    if not students:
        print("No students found.")
        return

    print(f"\n{'Name':<30} {'Org Defined ID':<16} Role")
    print(f"{'—' * 30} {'—' * 16} {'—' * 20}")
    for s in students:
        print(f"{s['name']:<30} {s['org_defined_id']:<16} {s['role']}")
    print(f"\n{len(students)} student(s) found.")

    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Classlist",
            "",
            "| Name | Org Defined ID | Role |",
            "|---|---|---|",
        ]
        for s in students:
            lines.append(f"| {s['name']} | {s['org_defined_id']} | {s['role']} |")
        lines.append("")
        (out / "classlist.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"Written to {out / 'classlist.md'}")


@app.command
def groups(
    class_id: Annotated[str, cyclopts.Parameter(help="Brightspace class identifier")],
    *,
    cdp_url: Annotated[
        str, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = "http://localhost:9222",
    base_url: Annotated[
        str, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = "https://dlo.mijnhva.nl",
    output_dir: Annotated[
        str | None,
        cyclopts.Parameter(help="Write a groups.md file to this directory"),
    ] = None,
) -> None:
    """List groups and their members for a class."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    browser, page = _connect_and_auth(cdp_url, base_url, class_id)

    try:
        navigate_to_groups(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    group_list = extract_groups(page)
    browser.close()

    if not group_list:
        print("No groups found.")
        return

    current_category = ""
    for g in group_list:
        if g["category"] != current_category:
            current_category = g["category"]
            print(f"\n[{current_category}]" if current_category else "")
        members = g["members"] if g["members"] else ""
        print(f"  {g['group_name']:<20} {members}")
    print(f"\n{len(group_list)} group(s) found.")

    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Groups",
            "",
            "| Category | Group | Members |",
            "|---|---|---|",
        ]
        for g in group_list:
            lines.append(f"| {g['category']} | {g['group_name']} | {g['members']} |")
        lines.append("")
        (out / "groups.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"Written to {out / 'groups.md'}")


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
    combined: Annotated[
        bool,
        cyclopts.Parameter(help="Also produce a single combined PDF of all groups"),
    ] = False,
) -> None:
    """Extract rubric feedback for specified class and assignments."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # --- validate CLI parameters (fail-fast) ---
    if category and not category_config:
        logger.error("--category requires --category-config to be specified")
        sys.exit(1)

    parsed_col_widths: tuple[int, int, int] = (3, 1, 6)
    if col_widths is not None:
        try:
            parsed_col_widths = _parse_col_widths(col_widths)
        except ValueError as exc:
            _fail_fast(exc)

    patterns: tuple[str, ...] | None = None
    if category:
        try:
            config = load_category_config(category_config)  # type: ignore[arg-type]
            patterns = get_patterns(config, category)
        except ConfigError as exc:
            _fail_fast(exc)

    # --- connect, auth, navigate to class ---
    browser, page = _connect_and_auth(cdp_url, base_url, class_id)

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

        if combined:
            combined_name = f"combined-{category}.pdf" if category else "combined.pdf"
            try:
                export_combined_pdf(output_dir, output_filename=combined_name)
                print(f"Combined PDF: {Path(output_dir) / combined_name}")
            except PdfExportError as exc:
                logger.warning("Failed to create combined PDF: %s", exc)
    else:
        write_feedback_files(groups, output_dir)
        print(
            f"\nDone. {len(groups)} group(s) processed. Output written to: {output_dir}"
        )

    browser.close()
