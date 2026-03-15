"""
Property-based tests for the OPM website.
"""

import os
import re
import yaml


INDEX_QMD = "index.qmd"

EXPECTED_RUBRIC_PATHS = [
    "sprint-2/opm-sprint-2-dma/rubric.md",
    "sprint-2/opm-sprint-2-meetplan-tbv-datacollectie/rubric.md",
]

ASSIGNMENTS = ["DMA", "Meetplan"]


def _read(path: str) -> str:
    assert os.path.exists(path), f"{path} not found"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Property: Site is a valid Quarto website
# ---------------------------------------------------------------------------


def test_site_config_valid():
    config_path = "_quarto.yml"
    assert os.path.exists(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    assert config is not None
    assert config.get("project", {}).get("type") == "website"


# ---------------------------------------------------------------------------
# Property: Rubric files exist
# ---------------------------------------------------------------------------


def test_rubric_files_exist():
    for path in EXPECTED_RUBRIC_PATHS:
        assert os.path.exists(path), f"Rubric not found: {path}"


# ---------------------------------------------------------------------------
# Property: Course name is "Operations (OPM)"
# ---------------------------------------------------------------------------


def test_course_name_correct():
    content = _read(INDEX_QMD)
    assert "Operationeel Procesmanagement" not in content
    assert "agentische" not in content.lower()


# ---------------------------------------------------------------------------
# Property: Title is "Beoordelingsprompts"
# ---------------------------------------------------------------------------


def test_title_correct():
    content = _read(INDEX_QMD)
    assert "Beoordelingsprompts" in content, "Title should be 'Beoordelingsprompts'"


# ---------------------------------------------------------------------------
# Property: Page metadata present
# ---------------------------------------------------------------------------


def test_page_metadata():
    content = _read(INDEX_QMD)
    assert "Opgesteld door:" in content
    assert "Opgesteld op:" in content
    assert "Aangepast door:" in content
    assert "Aangepast op:" in content


# ---------------------------------------------------------------------------
# Property: Sprint tabs present (Sprint 1, 2, 3)
# ---------------------------------------------------------------------------


def test_sprint_tabs_present():
    content = _read(INDEX_QMD)
    assert "{.panel-tabset}" in content, "Sprint tabs expected"
    assert "## Sprint 1" in content, "Sprint 1 tab expected"
    assert "## Sprint 2" in content, "Sprint 2 tab expected"
    assert "## Sprint 3" in content, "Sprint 3 tab expected"


# ---------------------------------------------------------------------------
# Property: Sprint 2 crosstab table with Verplicht/Optioneel columns
# ---------------------------------------------------------------------------


def test_crosstab_table_present():
    content = _read(INDEX_QMD)
    assert "<th>Verplicht</th>" in content
    assert "<th>Optioneel</th>" in content
    assert "<strong>DMA</strong>" in content
    assert "<strong>Meetplan</strong>" in content


# ---------------------------------------------------------------------------
# Property: Both assignments present
# ---------------------------------------------------------------------------


def test_both_assignments_in_page():
    content = _read(INDEX_QMD)
    for assignment in ASSIGNMENTS:
        assert assignment in content, f"Assignment '{assignment}' not found"


# ---------------------------------------------------------------------------
# Property: "eventueel te gebruiken aanvullende prompts" present
# ---------------------------------------------------------------------------


def test_aanvullende_prompts_description():
    content = _read(INDEX_QMD)
    assert "eventueel te gebruiken aanvullende prompts" in content


# ---------------------------------------------------------------------------
# Property: Synthetic dataset prompt is in Verplicht column for Meetplan
# ---------------------------------------------------------------------------


def test_synthetic_dataset_prompt_in_verplicht():
    content = _read(INDEX_QMD)
    match = re.search(
        r"<strong>Meetplan</strong></td>\s*<td>(.*?)</td>",
        content,
        re.DOTALL,
    )
    assert match, "Meetplan Verplicht cell not found"
    verplicht_cell = match.group(1)
    assert "synthetische dataset" in verplicht_cell
