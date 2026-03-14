"""
Property-based tests for the OPM Sprint 2 Webpage.
Uses pytest and PyYAML for parsing.
"""

import os
import re
import yaml
import pytest


SPRINT2_QMD = "sprint2.qmd"

# Tab labels (abbreviated) -> full group folder IDs
TAB_LABELS = ["E01", "E03", "F01"]
GROUP_FOLDERS = {
    "E01": "FC2E-01",
    "E03": "FC2E-03",
    "F01": "FC2F-01",
}

# Abbreviated assignment headings used in sprint2.qmd
ASSIGNMENTS = ["DMA", "Meetplan"]

EXPECTED_RUBRIC_PATHS = [
    "sprint-2/opm-sprint-2-dma/rubric.md",
    "sprint-2/opm-sprint-2-meetplan-tbv-datacollectie/rubric.md",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_navbar_entries(config: dict) -> list:
    entries = []
    navbar = config.get("website", {}).get("navbar", {})
    for side in ("left", "right", "center"):
        for item in navbar.get(side, []):
            if isinstance(item, dict) and "href" in item:
                entries.append(item["href"])
    return entries


def _read_sprint2() -> str:
    assert os.path.exists(SPRINT2_QMD), f"{SPRINT2_QMD} not found"
    with open(SPRINT2_QMD, "r", encoding="utf-8") as f:
        return f.read()


def _split_into_group_sections(content: str) -> dict:
    """Return dict mapping tab_label -> text of that group's tab section."""
    tabset_match = re.search(
        r"::: \{\.panel-tabset\}(.*?)^:::",
        content,
        re.DOTALL | re.MULTILINE,
    )
    assert tabset_match, "No {.panel-tabset} block found in sprint2.qmd"
    tabset_body = tabset_match.group(1)

    parts = re.split(r"(?=^## [A-Z]\d)", tabset_body, flags=re.MULTILINE)
    sections = {}
    for part in parts:
        m = re.match(r"^## ([A-Z]\d+)", part, re.MULTILINE)
        if m:
            sections[m.group(1)] = part
    return sections


# ---------------------------------------------------------------------------
# Property 9: Site config navbar includes Sprint 2
# ---------------------------------------------------------------------------

def test_property_9_site_config_navbar_includes_sprint2():
    config_path = "_quarto.yml"
    assert os.path.exists(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    assert config is not None
    assert config.get("project", {}).get("type") == "website"
    hrefs = _get_navbar_entries(config)
    assert "sprint2.qmd" in hrefs
    html_format = config.get("format", {}).get("html", {})
    assert html_format.get("theme") is not None
    assert html_format.get("css") is not None


# ---------------------------------------------------------------------------
# Property 5: Rubric files exist
# ---------------------------------------------------------------------------

def test_property_5_rubric_files_exist_at_expected_paths():
    for path in EXPECTED_RUBRIC_PATHS:
        assert os.path.exists(path), f"Rubric not found: {path}"


# ---------------------------------------------------------------------------
# Property 1: Tab count matches group count
# ---------------------------------------------------------------------------

def test_property_1_tab_count_matches_group_count():
    content = _read_sprint2()
    sections = _split_into_group_sections(content)
    assert len(sections) == len(TAB_LABELS), (
        f"Expected {len(TAB_LABELS)} tabs, found {len(sections)}: "
        f"{list(sections.keys())}"
    )
    for label in TAB_LABELS:
        assert label in sections, f"Tab '{label}' not found"


# ---------------------------------------------------------------------------
# Property 2: Both assignments present in every group tab
# ---------------------------------------------------------------------------

def test_property_2_both_assignments_in_every_group_tab():
    content = _read_sprint2()
    sections = _split_into_group_sections(content)
    for label in TAB_LABELS:
        tab_text = sections[label]
        for assignment in ASSIGNMENTS:
            assert f"### {assignment}" in tab_text, (
                f"Assignment '### {assignment}' not found in tab {label}"
            )


# ---------------------------------------------------------------------------
# Property 3: Input files present per group per assignment
# ---------------------------------------------------------------------------

def test_property_3_input_files_present_per_group_per_assignment():
    content = _read_sprint2()
    sections = _split_into_group_sections(content)
    for label in TAB_LABELS:
        group_folder = GROUP_FOLDERS[label]
        tab_text = sections[label]
        for assignment in ASSIGNMENTS:
            pattern = re.escape(f"### {assignment}") + r"(.*?)(?=^### |\Z)"
            match = re.search(pattern, tab_text, re.DOTALL | re.MULTILINE)
            assert match, f"'### {assignment}' not found in tab {label}"
            expected_prefix = f"submissions/sprint2/{group_folder}/"
            assert expected_prefix in match.group(1), (
                f"No input file link under '{expected_prefix}' in "
                f"'{assignment}' for {label}"
            )


# ---------------------------------------------------------------------------
# Property 4: Input file uniqueness across groups
# ---------------------------------------------------------------------------

def test_property_4_input_file_uniqueness_across_groups():
    content = _read_sprint2()
    sections = _split_into_group_sections(content)
    link_pattern = re.compile(r"\[.*?\]\((submissions/sprint2/[^\)]+)\)")
    seen: dict = {}
    for label, text in sections.items():
        for path in link_pattern.findall(text):
            if path in seen:
                pytest.fail(
                    f"Input file '{path}' in both '{seen[path]}' and '{label}'"
                )
            seen[path] = label
