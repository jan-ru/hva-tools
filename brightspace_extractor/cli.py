"""CLI entry point and pipeline orchestration using cyclopts."""

from __future__ import annotations

import logging
import os
import sys
import tomllib
from pathlib import Path
from typing import Annotated

import cyclopts
from playwright.sync_api import Browser, Page

from brightspace_extractor import __version__
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
    extract_quizzes,
    extract_rubrics,
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
    navigate_to_quizzes,
    navigate_to_rubrics,
)
from brightspace_extractor.parsing import parse_all_submissions
from brightspace_extractor.pdf_export import (
    check_pandoc_available,
    export_all_pdfs,
    export_combined_pdf,
    set_pandoc_path,
)
from brightspace_extractor.serialization import (
    group_to_filename,
    render_group_markdown_pandoc,
    write_feedback_files,
)

logger = logging.getLogger(__name__)

app = cyclopts.App(
    name="brightspace-extractor",
    help="Extract rubric feedback from Brightspace DLO.",
    version=__version__,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_CDP_DEFAULT = "http://localhost:9222"
_BASE_URL_DEFAULT = "https://dlo.mijnhva.nl"
_DEFAULT_CONFIG_PATH = "config/brightspace.toml"
_ENV_PREFIX = "BRIGHTSPACE_"


def _fail_fast(exc: Exception, browser=None) -> None:
    """Log an error and exit. Optionally close the browser first."""
    logger.error("%s", exc)
    if browser is not None:
        browser.close()
    sys.exit(1)


def _load_config(config_path: str | None = None) -> dict:
    """Load shared parameters from a TOML config file.

    Looks for ``config/brightspace.toml`` by default.
    Returns an empty dict if the file doesn't exist (unless an explicit
    path was given, in which case it raises).
    """
    path = Path(config_path) if config_path else Path(_DEFAULT_CONFIG_PATH)

    if not path.exists():
        if config_path:
            raise ConfigError(f"Config file not found: {config_path}")
        return {}

    try:
        data = tomllib.loads(path.read_bytes().decode())
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Malformed TOML in {path}: {exc}") from exc

    return data


def _cfg(config: dict, key: str, cli_value, default=None):
    """Resolve a parameter value with precedence: CLI → env var → config file → default.

    Environment variables are looked up as ``BRIGHTSPACE_{KEY}`` (uppercase).
    """
    if cli_value is not None:
        return cli_value
    env_value = os.environ.get(f"{_ENV_PREFIX}{key.upper()}")
    if env_value is not None:
        return env_value
    return config.get(key, default)


def _connect_and_verify(cdp_url: str) -> tuple[Browser, Page]:
    """Connect to browser and verify authentication. Returns (browser, page).

    Calls sys.exit(1) on any failure.
    """
    try:
        browser, _context, page = connect_to_browser(cdp_url)
    except ConnectionError as exc:
        _fail_fast(exc)

    try:
        if not verify_authentication(page):
            raise AuthenticationError(
                "Browser session is not authenticated.\n\n"
                "Please log in to Brightspace in your browser first (SSO, 2FA, etc.),\n"
                "then run this command again."
            )
    except AuthenticationError as exc:
        _fail_fast(exc, browser)

    return browser, page  # type: ignore[return-value]


def _connect_and_auth(
    cdp_url: str, base_url: str, class_id: str
) -> tuple[Browser, Page]:
    """Connect to browser, verify auth, navigate to class. Returns (browser, page).

    Calls sys.exit(1) on any failure.
    """
    browser, page = _connect_and_verify(cdp_url)

    try:
        navigate_to_class(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    return browser, page


def _resolve_common(
    config: str | None,
    cdp_url: str | None,
    base_url: str | None,
    class_id: str | None = None,
    output_dir: str | None = None,
    output_dir_default: str | None = None,
) -> tuple[dict, str, str, str | None, str | None]:
    """Load config and resolve common CLI parameters.

    Returns (cfg, cdp_url, base_url, class_id, output_dir).
    """
    cfg = _load_config(config)
    return (
        cfg,
        _cfg(cfg, "cdp_url", cdp_url, _CDP_DEFAULT),
        _cfg(cfg, "base_url", base_url, _BASE_URL_DEFAULT),
        _cfg(cfg, "class_id", class_id),
        _cfg(cfg, "output_dir", output_dir, output_dir_default),
    )


def _require_class_id(class_id: str | None) -> str:
    """Exit with error if class_id is missing."""
    if not class_id:
        logger.error("class_id is required (pass as argument or set in config file)")
        sys.exit(1)
    return class_id


def _setup_logging() -> None:
    """Configure logging: INFO+ to stderr so stdout stays clean for data output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def _print_and_write_table(
    items: list[dict],
    columns: list[tuple[str, str, int]],
    output_dir: str | None,
    filename: str,
    title: str,
) -> None:
    """Print a table to stdout and optionally write a markdown file.

    Args:
        items: List of dicts to display.
        columns: List of (header, dict_key, width) tuples.
        output_dir: Directory to write markdown file (None to skip).
        filename: Markdown filename (e.g. "classlist.md").
        title: Markdown heading (e.g. "# Classlist").
    """
    if not items:
        logger.info("No %s found.", title.lower().lstrip("# "))
        return

    # Data output → stdout
    header = "  ".join(f"{col[0]:<{col[2]}}" for col in columns)
    separator = "  ".join("—" * col[2] for col in columns)
    print(f"\n{header}")
    print(separator)
    for item in items:
        row = "  ".join(f"{str(item[col[1]]):<{col[2]}}" for col in columns)
        print(row)
    print(f"\n{len(items)} item(s) found.")

    # Write markdown
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        md_header = " | ".join(col[0] for col in columns)
        md_sep = "|".join("---" for _ in columns)
        lines = [title, "", f"| {md_header} |", f"|{md_sep}|"]
        for item in items:
            md_row = " | ".join(str(item[col[1]]) for col in columns)
            lines.append(f"| {md_row} |")
        lines.append("")
        (out / filename).write_text("\n".join(lines), encoding="utf-8")
        logger.info("Written to %s", out / filename)


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
    config: Annotated[
        str | None, cyclopts.Parameter(help="Path to config TOML file")
    ] = None,
    cdp_url: Annotated[
        str | None, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = None,
    base_url: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = None,
    output_dir: Annotated[
        str | None, cyclopts.Parameter(help="Write a courses.md file to this directory")
    ] = None,
) -> None:
    """List enrolled courses (class IDs) from the Brightspace homepage."""
    _setup_logging()
    _cfg_data, cdp_url, base_url, _, output_dir = _resolve_common(
        config, cdp_url, base_url, output_dir=output_dir
    )

    browser, page = _connect_and_verify(cdp_url)

    try:
        navigate_to_home(page, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    items = extract_courses(page)
    browser.close()

    _print_and_write_table(
        items,
        [("Class ID", "class_id", 12), ("Name", "name", 50)],
        output_dir,
        "courses.md",
        "# Courses",
    )


@app.command
def assignments(
    class_id: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace class identifier")
    ] = None,
    *,
    config: Annotated[
        str | None, cyclopts.Parameter(help="Path to config TOML file")
    ] = None,
    cdp_url: Annotated[
        str | None, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = None,
    base_url: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = None,
    output_dir: Annotated[
        str | None,
        cyclopts.Parameter(help="Write an assignments.md file to this directory"),
    ] = None,
) -> None:
    """List assignments (dropbox folders) for a class."""
    _setup_logging()
    _cfg_data, cdp_url, base_url, class_id, output_dir = _resolve_common(
        config, cdp_url, base_url, class_id, output_dir
    )
    class_id = _require_class_id(class_id)

    browser, page = _connect_and_auth(cdp_url, base_url, class_id)

    try:
        navigate_to_dropbox_list(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    items = extract_assignments(page)
    browser.close()

    _print_and_write_table(
        items,
        [("ID", "assignment_id", 12), ("Name", "name", 40)],
        output_dir,
        "assignments.md",
        "# Assignments",
    )


@app.command
def classlist(
    class_id: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace class identifier")
    ] = None,
    *,
    config: Annotated[
        str | None, cyclopts.Parameter(help="Path to config TOML file")
    ] = None,
    cdp_url: Annotated[
        str | None, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = None,
    base_url: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = None,
    output_dir: Annotated[
        str | None,
        cyclopts.Parameter(help="Write a classlist.md file to this directory"),
    ] = None,
    role: Annotated[
        str | None,
        cyclopts.Parameter(help="Filter by role (e.g. Student, 'Designing Lecturer')"),
    ] = "Student",
) -> None:
    """List students enrolled in a class."""
    _setup_logging()
    _cfg_data, cdp_url, base_url, class_id, output_dir = _resolve_common(
        config, cdp_url, base_url, class_id, output_dir
    )
    class_id = _require_class_id(class_id)

    browser, page = _connect_and_auth(cdp_url, base_url, class_id)

    try:
        navigate_to_classlist(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    students = extract_classlist(page)
    browser.close()

    if role:
        students = [s for s in students if s["role"].lower() == role.lower()]

    _print_and_write_table(
        students,
        [
            ("Name", "name", 30),
            ("Org Defined ID", "org_defined_id", 16),
            ("Role", "role", 20),
        ],
        output_dir,
        "classlist.md",
        "# Classlist",
    )


@app.command
def groups(
    class_id: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace class identifier")
    ] = None,
    *,
    config: Annotated[
        str | None, cyclopts.Parameter(help="Path to config TOML file")
    ] = None,
    cdp_url: Annotated[
        str | None, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = None,
    base_url: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = None,
    output_dir: Annotated[
        str | None,
        cyclopts.Parameter(help="Write a groups.md file to this directory"),
    ] = None,
) -> None:
    """List groups and their members for a class."""
    _setup_logging()
    _cfg_data, cdp_url, base_url, class_id, output_dir = _resolve_common(
        config, cdp_url, base_url, class_id, output_dir
    )
    class_id = _require_class_id(class_id)

    browser, page = _connect_and_auth(cdp_url, base_url, class_id)

    try:
        navigate_to_groups(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    group_list = extract_groups(page)
    browser.close()

    _print_and_write_table(
        group_list,
        [
            ("Category", "category", 20),
            ("Group", "group_name", 20),
            ("Members", "members", 10),
        ],
        output_dir,
        "groups.md",
        "# Groups",
    )


@app.command
def quizzes(
    class_id: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace class identifier")
    ] = None,
    *,
    config: Annotated[
        str | None, cyclopts.Parameter(help="Path to config TOML file")
    ] = None,
    cdp_url: Annotated[
        str | None, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = None,
    base_url: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = None,
    output_dir: Annotated[
        str | None,
        cyclopts.Parameter(help="Write a quizzes.md file to this directory"),
    ] = None,
) -> None:
    """List quizzes for a class."""
    _setup_logging()
    _cfg_data, cdp_url, base_url, class_id, output_dir = _resolve_common(
        config, cdp_url, base_url, class_id, output_dir
    )
    class_id = _require_class_id(class_id)

    browser, page = _connect_and_auth(cdp_url, base_url, class_id)

    try:
        navigate_to_quizzes(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    items = extract_quizzes(page)
    browser.close()

    _print_and_write_table(
        items,
        [("ID", "quiz_id", 10), ("Name", "name", 50)],
        output_dir,
        "quizzes.md",
        "# Quizzes",
    )


@app.command
def rubrics(
    class_id: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace class identifier")
    ] = None,
    *,
    config: Annotated[
        str | None, cyclopts.Parameter(help="Path to config TOML file")
    ] = None,
    cdp_url: Annotated[
        str | None, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = None,
    base_url: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = None,
    output_dir: Annotated[
        str | None,
        cyclopts.Parameter(help="Write a rubrics.md file to this directory"),
    ] = None,
) -> None:
    """List rubrics for a class."""
    _setup_logging()
    _cfg_data, cdp_url, base_url, class_id, output_dir = _resolve_common(
        config, cdp_url, base_url, class_id, output_dir
    )
    class_id = _require_class_id(class_id)

    browser, page = _connect_and_auth(cdp_url, base_url, class_id)

    try:
        navigate_to_rubrics(page, class_id, base_url=base_url)
    except NavigationError as exc:
        _fail_fast(exc, browser)

    items = extract_rubrics(page)
    browser.close()

    _print_and_write_table(
        items,
        [
            ("ID", "rubric_id", 8),
            ("Name", "name", 40),
            ("Type", "type", 12),
            ("Scoring", "scoring_method", 16),
            ("Status", "status", 12),
        ],
        output_dir,
        "rubrics.md",
        "# Rubrics",
    )


@app.command
def extract(
    class_id: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace class identifier")
    ] = None,
    assignment_ids: Annotated[
        list[str] | None, cyclopts.Parameter(help="One or more assignment identifiers")
    ] = None,
    *,
    config: Annotated[
        str | None, cyclopts.Parameter(help="Path to config TOML file")
    ] = None,
    output_dir: Annotated[
        str | None, cyclopts.Parameter(help="Output directory for markdown files")
    ] = None,
    cdp_url: Annotated[
        str | None, cyclopts.Parameter(help="Playwright CDP endpoint")
    ] = None,
    base_url: Annotated[
        str | None, cyclopts.Parameter(help="Brightspace instance base URL")
    ] = None,
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
    _setup_logging()
    cfg, cdp_url, base_url, class_id, output_dir = _resolve_common(
        config, cdp_url, base_url, class_id, output_dir, output_dir_default="./output"
    )
    class_id = _require_class_id(class_id)

    # Resolve pandoc path from config (supports non-PATH installs like scoop)
    pandoc_path = _cfg(cfg, "pandoc_path", None, "pandoc")
    set_pandoc_path(pandoc_path)

    if not assignment_ids:
        logger.error(
            "assignment_ids are required (pass as arguments or set in config file)"
        )
        sys.exit(1)

    parsed_col_widths: tuple[int, int, int] = (3, 1, 6)
    if col_widths is not None:
        try:
            parsed_col_widths = _parse_col_widths(col_widths)
        except ValueError as exc:
            _fail_fast(exc)

    patterns: tuple[str, ...] | None = None
    if category:
        category_config = category_config or cfg.get("category_config")
        if not category_config:
            logger.error("--category requires --category-config to be specified")
            sys.exit(1)
        try:
            cat_cfg = load_category_config(category_config)
            patterns = get_patterns(cat_cfg, category)
        except ConfigError as exc:
            _fail_fast(exc)

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
        logger.info("Processing assignment: %s", assignment_name)

        raw_submissions = extract_group_submissions(page)
        for raw in raw_submissions:
            logger.info("  Processing group: %s", raw.get("group_name", "<unknown>"))

        feedbacks = parse_all_submissions(
            raw_submissions, assignment_name, assignment_id
        )
        all_feedbacks.extend(feedbacks)

    # --- filter (optional) → aggregate → serialize → write ---
    if patterns is not None:
        all_feedbacks = [
            filter_assignment_feedback(af, patterns) for af in all_feedbacks
        ]

    groups_result = aggregate_by_group(all_feedbacks)

    if pdf:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for gf in groups_result:
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
        logger.info(
            "Done. %d group(s) processed. PDF: %d succeeded, %d failed. Output: %s",
            len(groups_result),
            success,
            failure,
            output_dir,
        )

        if combined:
            combined_name = f"combined-{category}.pdf" if category else "combined.pdf"
            try:
                export_combined_pdf(output_dir, output_filename=combined_name)
                logger.info("Combined PDF: %s", Path(output_dir) / combined_name)
            except PdfExportError as exc:
                logger.warning("Failed to create combined PDF: %s", exc)
    else:
        write_feedback_files(groups_result, output_dir)
        logger.info(
            "Done. %d group(s) processed. Output: %s",
            len(groups_result),
            output_dir,
        )

    browser.close()
