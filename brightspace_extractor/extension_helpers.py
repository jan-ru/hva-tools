"""Pure-Python equivalents of browser extension helper functions.

These mirror the logic in ``extension/popup.js`` so that property-based tests
can validate correctness using Hypothesis.  The JavaScript extension uses
identical patterns and logic.
"""

from __future__ import annotations

import re

PAGE_PATTERNS: dict[str, re.Pattern[str]] = {
    "classlist": re.compile(r"classlist\.d2l"),
    "assignments": re.compile(r"folders_manage\.d2l"),
    "groups": re.compile(r"group_list\.d2l"),
    "quizzes": re.compile(r"quizzes_manage\.d2l"),
    "rubrics": re.compile(r"rubrics/list\.d2l"),
    "submissions": re.compile(r"folder_submissions_users\.d2l"),
}


def detect_page_type(url: str) -> str | None:
    """Return the Brightspace page type for *url*, or ``None``."""
    for page_type, pattern in PAGE_PATTERNS.items():
        if pattern.search(url):
            return page_type
    return None


def table_to_tsv(rows: list[dict[str, str]]) -> str:
    """Convert a list of dicts to a TSV string (header + data rows)."""
    if not rows:
        return ""
    keys = list(rows[0].keys())
    header = "\t".join(keys)
    lines = ["\t".join(str(row.get(k, "")) for k in keys) for row in rows]
    return "\n".join([header, *lines])
