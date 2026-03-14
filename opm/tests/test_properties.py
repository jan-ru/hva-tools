"""
Property-based tests for the OPM Sprint 2 Webpage.
Uses pytest and PyYAML for parsing.
"""

import os
import yaml
import pytest


# ---------------------------------------------------------------------------
# Property 9: Site config navbar includes Sprint 2
# Validates: Requirements 1.2, 10.1, 10.2
# ---------------------------------------------------------------------------

def _get_navbar_entries(config: dict) -> list:
    """Recursively collect all navbar href entries from _quarto.yml."""
    entries = []
    navbar = config.get("website", {}).get("navbar", {})
    for side in ("left", "right", "center"):
        for item in navbar.get(side, []):
            if isinstance(item, dict) and "href" in item:
                entries.append(item["href"])
    return entries


def test_property_9_site_config_navbar_includes_sprint2():
    """
    Property 9: Site config navbar includes Sprint 2
    Validates: Requirements 1.2, 10.1, 10.2

    Parse _quarto.yml and assert that at least one navbar entry has
    href: sprint2.qmd.
    """
    config_path = "_quarto.yml"
    assert os.path.exists(config_path), f"_quarto.yml not found at {config_path}"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert config is not None, "_quarto.yml is empty or invalid"

    # Requirement 1.1: project type must be website
    assert config.get("project", {}).get("type") == "website", \
        "project.type must be 'website'"

    # Requirement 1.2 / 10.1: navbar must include sprint2.qmd
    hrefs = _get_navbar_entries(config)
    assert "sprint2.qmd" in hrefs, (
        f"No navbar entry with href: sprint2.qmd found. "
        f"Found entries: {hrefs}"
    )

    # Requirement 1.3: HTML theme and CSS must be configured
    html_format = config.get("format", {}).get("html", {})
    assert html_format.get("theme") is not None, \
        "format.html.theme must be set"
    assert html_format.get("css") is not None, \
        "format.html.css must reference styles.css"


# ---------------------------------------------------------------------------
# Property 5: Rubric link correctness per assignment
# Validates: Requirements 5.1, 5.2, 5.6
# ---------------------------------------------------------------------------

EXPECTED_RUBRIC_PATHS = [
    "sprint-2/opm-sprint-2-dma/rubric.md",
    "sprint-2/opm-sprint-2-meetplan-tbv-datacollectie/rubric.md",
]


def test_property_5_rubric_files_exist_at_expected_paths():
    """
    Property 5: Rubric link correctness per assignment
    Validates: Requirements 5.1, 5.2, 5.6

    Assert both rubric files exist at their exact expected paths.
    """
    for path in EXPECTED_RUBRIC_PATHS:
        assert os.path.exists(path), (
            f"Rubric file not found at expected path: {path}"
        )


# ---------------------------------------------------------------------------
# Helpers for parsing sprint2.qmd
# ---------------------------------------------------------------------------

SPRINT2_QMD = "sprint2.qmd"
GROUPS = ["FC2E-01", "FC2E-03", "FC2F-01"]
ASSIGNMENTS = [
    "OPM Sprint 2 DMA",
    "OPM Sprint 2 - Meetplan tbv Datacollectie",
]


def _read_sprint2() -> str:
    assert os.path.exists(SPRINT2_QMD), f"{SPRINT2_QMD} not found"
    with open(SPRINT2_QMD, "r", encoding="utf-8") as f:
        return f.read()


def _split_into_group_sections(content: str) -> dict:
    """
    Return a dict mapping group_id -> text of that group's tab section.
    Splits on '## FC*' headings inside the tabset.
    """
    import re
    # Find the tabset block
    tabset_match = re.search(
        r"::: \{\.panel-tabset\}(.*?)^:::",
        content,
        re.DOTALL | re.MULTILINE,
    )
    assert tabset_match, "No {.panel-tabset} block found in sprint2.qmd"
    tabset_body = tabset_match.group(1)

    # Split on ## FC headings
    parts = re.split(r"(?=^## FC)", tabset_body, flags=re.MULTILINE)
    sections = {}
    for part in parts:
        m = re.match(r"^## (FC[\w-]+)", part, re.MULTILINE)
        if m:
            sections[m.group(1)] = part
    return sections


# ---------------------------------------------------------------------------
# Property 1: Tab count matches group count
# Validates: Requirements 2.1, 2.3
# ---------------------------------------------------------------------------

def test_property_1_tab_count_matches_group_count():
    """
    Property 1: Tab count matches group count
    Validates: Requirements 2.1, 2.3

    The number of ## FC* headings inside the tabset equals the number of
    defined groups (3).
    """
    import re
    content = _read_sprint2()
    sections = _split_into_group_sections(content)
    assert len(sections) == len(GROUPS), (
        f"Expected {len(GROUPS)} group tabs, found {len(sections)}: "
        f"{list(sections.keys())}"
    )
    for group in GROUPS:
        assert group in sections, (
            f"Group tab '{group}' not found in sprint2.qmd tabset"
        )


# ---------------------------------------------------------------------------
# Property 2: Both assignments present in every group tab
# Validates: Requirements 3.1, 3.3
# ---------------------------------------------------------------------------

def test_property_2_both_assignments_in_every_group_tab():
    """
    Property 2: Both assignments present in every group tab
    Validates: Requirements 3.1, 3.3

    Each group tab must contain headings for both assignment names.
    """
    content = _read_sprint2()
    sections = _split_into_group_sections(content)

    for group in GROUPS:
        assert group in sections, f"Group '{group}' tab not found"
        tab_text = sections[group]
        for assignment in ASSIGNMENTS:
            assert assignment in tab_text, (
                f"Assignment '{assignment}' heading not found in tab for {group}"
            )


# ---------------------------------------------------------------------------
# Property 3: Input files present per group per assignment
# Validates: Requirements 4.1, 4.2
# ---------------------------------------------------------------------------

def test_property_3_input_files_present_per_group_per_assignment():
    """
    Property 3: Input files present per group per assignment
    Validates: Requirements 4.1, 4.2

    Each group+assignment section must contain at least one link under
    submissions/sprint2/{group-id}/.
    """
    import re
    content = _read_sprint2()
    sections = _split_into_group_sections(content)

    for group in GROUPS:
        assert group in sections, f"Group '{group}' tab not found"
        tab_text = sections[group]

        # Split tab into assignment sub-sections
        # Each assignment starts with ### <assignment name>
        for assignment in ASSIGNMENTS:
            # Find the assignment section within the tab
            pattern = re.escape(f"### {assignment}") + r"(.*?)(?=^### |\Z)"
            match = re.search(pattern, tab_text, re.DOTALL | re.MULTILINE)
            assert match, (
                f"Assignment section '### {assignment}' not found in tab for {group}"
            )
            section_text = match.group(1)

            # Check for at least one link under submissions/sprint2/{group}/
            expected_prefix = f"submissions/sprint2/{group}/"
            assert expected_prefix in section_text, (
                f"No input file link under '{expected_prefix}' found "
                f"in '{assignment}' section for group {group}"
            )


# ---------------------------------------------------------------------------
# Property 4 / Task 3.1: Input file uniqueness across groups
# Validates: Requirements 4.3
# ---------------------------------------------------------------------------

def test_property_4_input_file_uniqueness_across_groups():
    """
    Property 4: Input file uniqueness across groups
    Validates: Requirements 4.3

    No input file path appears in more than one group's section.
    """
    import re
    content = _read_sprint2()
    sections = _split_into_group_sections(content)

    # Collect all file paths per group
    link_pattern = re.compile(r"\[.*?\]\((submissions/sprint2/[^\)]+)\)")
    group_files: dict = {}
    for group, text in sections.items():
        group_files[group] = set(link_pattern.findall(text))

    # Check no path appears in more than one group
    all_paths: list = []
    for group, paths in group_files.items():
        for path in paths:
            all_paths.append((path, group))

    seen: dict = {}
    for path, group in all_paths:
        if path in seen:
            pytest.fail(
                f"Input file path '{path}' appears in both group "
                f"'{seen[path]}' and '{group}' — paths must be unique per group"
            )
        seen[path] = group


# ---------------------------------------------------------------------------
# Property 6 / Task 4.4: No placeholder text in Prompts sections
# Validates: Requirements 6.1, 6.2, 6.4
# ---------------------------------------------------------------------------

def test_property_6_no_placeholder_text_in_prompts():
    """
    Property 6: Prompt completeness and no placeholder text
    Validates: Requirements 6.1, 6.2, 6.4

    No text matching [.*?] appears inside a Prompts section.
    """
    import re
    content = _read_sprint2()
    sections = _split_into_group_sections(content)

    placeholder_pattern = re.compile(r"\[.*?\]")

    for group in GROUPS:
        assert group in sections, f"Group '{group}' tab not found"
        tab_text = sections[group]

        for assignment in ASSIGNMENTS:
            # Find the Prompts sub-section within this assignment section
            assign_pattern = re.escape(f"### {assignment}") + r"(.*?)(?=^### |\Z)"
            assign_match = re.search(
                assign_pattern, tab_text, re.DOTALL | re.MULTILINE
            )
            assert assign_match, (
                f"Assignment '### {assignment}' not found in tab for {group}"
            )
            assign_text = assign_match.group(1)

            # Find the Prompts sub-section
            prompts_match = re.search(
                r"#### Prompts(.*?)(?=^#### |\Z)",
                assign_text,
                re.DOTALL | re.MULTILINE,
            )
            assert prompts_match, (
                f"No '#### Prompts' section found in '{assignment}' for {group}"
            )
            prompts_text = prompts_match.group(1)

            # Check for placeholder text — but allow markdown links [text](url)
            # We only flag bare [...] that are NOT followed by (
            bare_placeholder = re.compile(r"\[[^\]]*\](?!\()")
            matches = bare_placeholder.findall(prompts_text)
            assert not matches, (
                f"Placeholder text found in Prompts section of '{assignment}' "
                f"for group {group}: {matches}"
            )


# ---------------------------------------------------------------------------
# Property 7 / Task 7.1: Shared prompt text consistency
# Validates: Requirements 6.3
# ---------------------------------------------------------------------------

def _extract_prompts_per_assignment(content: str) -> dict:
    """
    Parse sprint2.qmd and return a nested dict:
      { assignment_name: { prompt_id: [text, ...] } }
    where each list contains the prompt text from every group that uses it.
    """
    import re

    sections = _split_into_group_sections(content)

    # assignment -> prompt_id -> list of texts (one per group occurrence)
    result: dict = {}

    for group, tab_text in sections.items():
        for assignment in ASSIGNMENTS:
            # Find the assignment section within the tab
            assign_pattern = re.escape(f"### {assignment}") + r"(.*?)(?=^### |\Z)"
            assign_match = re.search(
                assign_pattern, tab_text, re.DOTALL | re.MULTILINE
            )
            if not assign_match:
                continue
            assign_text = assign_match.group(1)

            # Find the Prompts sub-section
            prompts_match = re.search(
                r"#### Prompts(.*?)(?=^#### |\Z)",
                assign_text,
                re.DOTALL | re.MULTILINE,
            )
            if not prompts_match:
                continue
            prompts_text = prompts_match.group(1)

            # Split on ##### <prompt-id> headings
            prompt_parts = re.split(r"(?=^##### )", prompts_text, flags=re.MULTILINE)
            for part in prompt_parts:
                id_match = re.match(r"^##### ([\w-]+)\s*\n(.*)", part, re.DOTALL)
                if not id_match:
                    continue
                prompt_id = id_match.group(1)
                prompt_text = id_match.group(2).strip()

                result.setdefault(assignment, {}).setdefault(prompt_id, [])
                result[assignment][prompt_id].append(prompt_text)

    return result


def test_property_7_shared_prompt_text_consistency():
    """
    Property 7: Shared prompt text consistency
    Validates: Requirements 6.3

    For any prompt identifier that appears in multiple groups for the same
    assignment, the prompt text must be identical across all occurrences.
    """
    content = _read_sprint2()
    prompts_by_assignment = _extract_prompts_per_assignment(content)

    for assignment, prompts in prompts_by_assignment.items():
        for prompt_id, texts in prompts.items():
            if len(texts) > 1:
                first = texts[0]
                for i, text in enumerate(texts[1:], start=2):
                    assert text == first, (
                        f"Prompt '{prompt_id}' in assignment '{assignment}' "
                        f"has inconsistent text across groups.\n"
                        f"Occurrence 1:\n{first}\n\n"
                        f"Occurrence {i}:\n{text}"
                    )
