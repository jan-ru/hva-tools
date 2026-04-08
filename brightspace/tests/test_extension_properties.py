"""Property-based tests for browser extension helper logic.

Property 3: URL Pattern Detection
    Known Brightspace URLs map to the correct page type; non-Brightspace
    URLs return None.

Property 4: Table-to-TSV Conversion Preserves Content
    Converting a list of dicts to TSV preserves line count, field count,
    and field values.
"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from brightspace_extractor.extension_helpers import (
    PAGE_PATTERNS,
    detect_page_type,
    table_to_tsv,
)

# ── Property 3: URL Pattern Detection ────────────────────────────────────────

_class_id_st = st.integers(min_value=1000, max_value=999999).map(str)
_query_st = st.text(
    alphabet=st.characters(
        min_codepoint=0x30, max_codepoint=0x7A, categories=("L", "N")
    ),
    min_size=0,
    max_size=30,
)

# Map page type → URL template (the {ou} and {extra} placeholders are filled by strategies)
_URL_TEMPLATES: dict[str, str] = {
    "classlist": "https://dlo.mijnhva.nl/d2l/lms/classlist/classlist.d2l?ou={ou}{extra}",
    "assignments": "https://dlo.mijnhva.nl/d2l/lms/dropbox/admin/folders_manage.d2l?ou={ou}{extra}",
    "groups": "https://dlo.mijnhva.nl/d2l/lms/group/group_list.d2l?ou={ou}{extra}",
    "quizzes": "https://dlo.mijnhva.nl/d2l/lms/quizzing/admin/quizzes_manage.d2l?ou={ou}{extra}",
    "rubrics": "https://dlo.mijnhva.nl/d2l/lp/rubrics/list.d2l?ou={ou}{extra}",
    "submissions": "https://dlo.mijnhva.nl/d2l/lms/dropbox/admin/folder_submissions_users.d2l?db=12345&ou={ou}{extra}",
}


@given(
    page_type=st.sampled_from(sorted(_URL_TEMPLATES.keys())),
    ou=_class_id_st,
    extra=_query_st,
)
@settings(max_examples=200)
def test_known_urls_detected_correctly(page_type: str, ou: str, extra: str) -> None:
    """Feature: browser-extension-api, Property 3: URL pattern detection (known URLs)"""
    url = _URL_TEMPLATES[page_type].format(ou=ou, extra=extra)
    assert detect_page_type(url) == page_type


# Strategy for URLs that should NOT match any Brightspace pattern.
# We generate generic URLs and filter out anything that accidentally matches.
_safe_path_st = st.text(
    alphabet=st.characters(min_codepoint=0x61, max_codepoint=0x7A),  # a-z only
    min_size=1,
    max_size=30,
)


def _is_non_brightspace(url: str) -> bool:
    """Return True if the URL does not match any known pattern."""
    return all(not p.search(url) for p in PAGE_PATTERNS.values())


@given(
    domain=st.sampled_from(
        ["https://example.com", "https://google.com", "https://canvas.instructure.com"]
    ),
    path=_safe_path_st,
)
@settings(max_examples=200)
def test_non_brightspace_urls_return_none(domain: str, path: str) -> None:
    """Feature: browser-extension-api, Property 3: URL pattern detection (non-Brightspace URLs)"""
    url = f"{domain}/{path}"
    if not _is_non_brightspace(url):
        return  # skip accidental matches
    assert detect_page_type(url) is None


# ── Property 4: Table-to-TSV Conversion Preserves Content ───────────────────

# Strategy: generate dicts with consistent keys and printable string values
# (no tabs or newlines, which would break TSV structure).
_cell_st = st.text(
    alphabet=st.characters(
        categories=("L", "N", "Zs"),
        min_codepoint=0x20,
        max_codepoint=0x024F,
    ),
    min_size=0,
    max_size=30,
).filter(lambda s: "\t" not in s and "\n" not in s and "\r" not in s)

_FIXED_KEYS = ["name", "id", "value"]

_row_st = st.fixed_dictionaries({k: _cell_st for k in _FIXED_KEYS})


@given(rows=st.lists(_row_st, min_size=1, max_size=20))
@settings(max_examples=200)
def test_tsv_preserves_content(rows: list[dict[str, str]]) -> None:
    """Feature: browser-extension-api, Property 4: Table-to-TSV conversion preserves content"""
    tsv = table_to_tsv(rows)
    lines = tsv.split("\n")

    # Header + one line per row
    assert len(lines) == len(rows) + 1

    # Header has correct keys
    header_fields = lines[0].split("\t")
    assert header_fields == _FIXED_KEYS

    # Each data line has correct field count and values
    for i, row in enumerate(rows):
        fields = lines[i + 1].split("\t")
        assert len(fields) == len(_FIXED_KEYS)
        for j, key in enumerate(_FIXED_KEYS):
            assert fields[j] == str(row[key])


@given(rows=st.just([]))
def test_tsv_empty_input(rows: list[dict[str, str]]) -> None:
    """Feature: browser-extension-api, Property 4: Table-to-TSV conversion (empty input)"""
    assert table_to_tsv(rows) == ""
