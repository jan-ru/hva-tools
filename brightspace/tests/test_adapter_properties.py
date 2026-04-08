"""Property-based tests for the ExtractionAdapter.

Property 1: Adapter–Playwright Extraction Equivalence
    For each HTML fixture, extracting with the adapter produces identical
    output to extracting with Playwright.

Property 2: Listing Extraction Structural Correctness
    For generated Brightspace-structured HTML, extraction via adapter returns
    correctly structured output with expected keys and counts.
"""

from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from brightspace_extractor.adapter import ExtractionAdapter
from brightspace_extractor.extraction import (
    _scrape_group_table,
    extract_assignments,
    extract_classlist,
    extract_quizzes,
    extract_rubrics,
)

FIXTURES_DIR = Path(__file__).parent

# ── Property 1: Adapter–Playwright Extraction Equivalence ────────────────────

FIXTURE_CONFIGS = [
    ("assignments-debug.html", extract_assignments),
    ("classlist-debug.html", extract_classlist),
    ("quizzes-debug.html", extract_quizzes),
    ("rubrics-debug.html", extract_rubrics),
    ("groups-debug.html", _scrape_group_table),
]


@pytest.mark.parametrize(
    "fixture_name,extract_fn",
    FIXTURE_CONFIGS,
    ids=[c[0].removesuffix("-debug.html") for c in FIXTURE_CONFIGS],
)
def test_adapter_playwright_equivalence(pw_browser, fixture_name, extract_fn) -> None:
    """Feature: browser-extension-api, Property 1: Adapter-Playwright extraction equivalence"""
    fixture_path = FIXTURES_DIR / fixture_name
    html = fixture_path.read_text(encoding="utf-8")

    # Playwright path
    page = pw_browser.new_page()
    page.goto(fixture_path.as_uri())
    pw_result = extract_fn(page)
    page.close()

    # Adapter path
    adapter = ExtractionAdapter(html)
    adapter_result = extract_fn(adapter)

    assert adapter_result == pw_result


# ── Property 2: Listing Extraction Structural Correctness ────────────────────

# Hypothesis strategies for generating Brightspace-structured HTML

_name_st = st.text(
    alphabet=st.characters(
        categories=("L", "N", "Zs"), min_codepoint=32, max_codepoint=0x024F
    ),
    min_size=1,
    max_size=20,
).filter(lambda s: s.strip() != "")

_id_st = st.integers(min_value=10000, max_value=999999).map(str)


def _classlist_html(students: list[tuple[str, str, str]]) -> str:
    """Build minimal Brightspace classlist HTML from (name, org_id, role) tuples."""
    rows = []
    for name, org_id, role in students:
        rows.append(
            f'<tr><th scope="row" class="d_ich">'
            f'<a class="d2l-link d2l-link-inline">{name}</a></th>'
            f'<td class="d_gn"><label>{org_id}</label></td>'
            f'<td class="d_gn"><label>{role}</label></td></tr>'
        )
    return '<table class="d2l-table d_gl">' + "".join(rows) + "</table>"


def _assignments_html(assignments: list[tuple[str, str]]) -> str:
    """Build minimal Brightspace assignments HTML from (id, name) tuples."""
    links = []
    for aid, name in assignments:
        links.append(
            f'<a href="/d2l/lms/dropbox/admin/folder_submissions_users.d2l?db={aid}&ou=123">'
            f"{name}</a>"
        )
    return "<html><body>" + "".join(links) + "</body></html>"


def _quizzes_html(quizzes: list[tuple[str, str]]) -> str:
    """Build minimal Brightspace quizzes HTML from (id, name) tuples."""
    links = []
    for qid, name in quizzes:
        links.append(
            f'<a href="/d2l/lms/quizzing/admin/quiz_newedit_properties.d2l?qi={qid}&ou=123">'
            f"{name}</a>"
        )
    return "<html><body>" + "".join(links) + "</body></html>"


def _rubrics_html(rubrics: list[tuple[str, str, str, str, str]]) -> str:
    """Build minimal Brightspace rubrics HTML from (id, name, type, scoring, status) tuples."""
    rows = []
    for rid, name, rtype, scoring, status in rubrics:
        rows.append(
            f'<tr><th scope="row" class="d_ich">'
            f'<a class="d2l-link" href="/d2l/lp/rubrics/list.d2l?rubricId={rid}&ou=123">{name}</a></th>'
            f"<td><span>{rtype}</span></td>"
            f"<td><span>{scoring}</span></td>"
            f"<td><span>{status}</span></td></tr>"
        )
    return '<table class="d2l-table d_gl">' + "".join(rows) + "</table>"


def _groups_html(groups: list[tuple[str, str]]) -> str:
    """Build minimal Brightspace groups HTML from (name, members) tuples."""
    rows = []
    for gname, members in groups:
        rows.append(
            f'<tr><th scope="row" class="d_ich">'
            f'<a class="d2l-link">{gname}</a></th>'
            f'<td class="d_gc">{members}</td></tr>'
        )
    return '<table class="d2l-table d_gl">' + "".join(rows) + "</table>"


# ── Classlist structural correctness ─────────────────────────────────────────

_classlist_entry_st = st.tuples(
    _name_st, _id_st, st.sampled_from(["Student", "Lecturer"])
)


@given(entries=st.lists(_classlist_entry_st, min_size=1, max_size=10))
@settings(max_examples=100)
def test_classlist_structural_correctness(entries) -> None:
    """Feature: browser-extension-api, Property 2: Listing extraction structural correctness (classlist)"""
    html = _classlist_html(entries)
    adapter = ExtractionAdapter(html)
    results = extract_classlist(adapter)

    assert len(results) == len(entries)
    for r in results:
        assert set(r.keys()) == {"name", "org_defined_id", "role"}
        assert r["name"].strip() != ""


# ── Assignments structural correctness ───────────────────────────────────────

_assignment_entry_st = st.tuples(_id_st, _name_st)


@given(entries=st.lists(_assignment_entry_st, min_size=1, max_size=10))
@settings(max_examples=100)
def test_assignments_structural_correctness(entries) -> None:
    """Feature: browser-extension-api, Property 2: Listing extraction structural correctness (assignments)"""
    html = _assignments_html(entries)
    adapter = ExtractionAdapter(html)
    results = extract_assignments(adapter)

    assert len(results) == len(entries)
    for r in results:
        assert set(r.keys()) == {"assignment_id", "name"}
        assert r["assignment_id"].strip() != ""
        assert r["name"].strip() != ""


# ── Quizzes structural correctness ───────────────────────────────────────────

_quiz_entry_st = st.tuples(_id_st, _name_st)


@given(entries=st.lists(_quiz_entry_st, min_size=1, max_size=10))
@settings(max_examples=100)
def test_quizzes_structural_correctness(entries) -> None:
    """Feature: browser-extension-api, Property 2: Listing extraction structural correctness (quizzes)"""
    html = _quizzes_html(entries)
    adapter = ExtractionAdapter(html)
    results = extract_quizzes(adapter)

    assert len(results) == len(entries)
    for r in results:
        assert set(r.keys()) == {"quiz_id", "name"}
        assert r["quiz_id"].strip() != ""
        assert r["name"].strip() != ""


# ── Rubrics structural correctness ───────────────────────────────────────────

_rubric_entry_st = st.tuples(
    _id_st,
    _name_st,
    st.sampled_from(["Analytic", "Holistic"]),
    st.sampled_from(["Text Only", "Percentages", "Points", "Custom Points"]),
    st.sampled_from(["Draft", "Published", "Archived"]),
)


@given(entries=st.lists(_rubric_entry_st, min_size=1, max_size=10))
@settings(max_examples=100)
def test_rubrics_structural_correctness(entries) -> None:
    """Feature: browser-extension-api, Property 2: Listing extraction structural correctness (rubrics)"""
    html = _rubrics_html(entries)
    adapter = ExtractionAdapter(html)
    results = extract_rubrics(adapter)

    assert len(results) == len(entries)
    for r in results:
        assert set(r.keys()) == {
            "rubric_id",
            "name",
            "type",
            "scoring_method",
            "status",
        }
        assert r["rubric_id"].strip() != ""
        assert r["name"].strip() != ""


# ── Groups structural correctness ────────────────────────────────────────────

_members_st = st.tuples(
    st.integers(min_value=0, max_value=10),
    st.integers(min_value=1, max_value=10),
).map(lambda t: f"{t[0]}/{t[1]}")

_group_entry_st = st.tuples(_name_st, _members_st)


@given(entries=st.lists(_group_entry_st, min_size=1, max_size=10))
@settings(max_examples=100)
def test_groups_structural_correctness(entries) -> None:
    """Feature: browser-extension-api, Property 2: Listing extraction structural correctness (groups)"""
    html = _groups_html(entries)
    adapter = ExtractionAdapter(html)
    results = _scrape_group_table(adapter)

    assert len(results) == len(entries)
    for r in results:
        assert set(r.keys()) == {"group_name", "members"}
        assert r["group_name"].strip() != ""
