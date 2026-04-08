"""Property-based and unit tests for the filtering module."""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from brightspace_extractor.exceptions import ConfigError
from brightspace_extractor.filtering import (
    filter_rubric,
    load_category_config,
    matches_any_pattern,
)
from brightspace_extractor.models import Criterion, RubricFeedback


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# A category name: at least 1 alphanumeric char (TOML bare-key safe)
_category_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=1,
    max_size=10,
)

# An invalid pattern: either empty string or whitespace-only
_invalid_pattern = st.one_of(
    st.just(""),
    st.text(alphabet=" \t", min_size=1, max_size=5),
)

# A valid pattern (non-empty, has at least one non-whitespace char)
_valid_pattern = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters=" -"),
    min_size=1,
    max_size=20,
).filter(lambda s: s.strip() != "")


def _toml_escape(s: str) -> str:
    """Escape a string for use inside a TOML double-quoted value."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\t", "\\t")


def _categories_to_toml(categories: dict[str, list[str]]) -> str:
    """Serialize a categories dict to a TOML string."""
    lines = ["[categories]"]
    for name, patterns in categories.items():
        items = ", ".join(f'"{_toml_escape(p)}"' for p in patterns)
        lines.append(f"{name} = [{items}]")
    return "\n".join(lines)


def _invalid_categories_dict():
    """Strategy producing a categories dict that has at least one invalid entry.

    Invalid means either:
      - a category maps to an empty list, OR
      - a category's pattern list contains at least one empty/whitespace-only string
    """
    # Case A: category with an empty pattern list
    empty_list_entry = _category_name.map(lambda name: {name: []})

    # Case B: category whose list contains at least one bad pattern
    list_with_bad_pattern = st.tuples(
        _category_name,
        st.lists(_valid_pattern, min_size=0, max_size=3),
        _invalid_pattern,
        st.lists(_valid_pattern, min_size=0, max_size=3),
    ).map(lambda t: {t[0]: t[1] + [t[2]] + t[3]})

    return st.one_of(empty_list_entry, list_with_bad_pattern)


# ---------------------------------------------------------------------------
# Property 1: Config validation rejects invalid patterns
# Tag: Feature: criteria-filtering-pdf-export, Property 1: Config validation rejects invalid patterns
# Validates: Requirements 1.2
# ---------------------------------------------------------------------------


@given(bad_categories=_invalid_categories_dict())
@settings(max_examples=200)
def test_property_config_validation_rejects_invalid_patterns(
    bad_categories: dict[str, list[str]],
) -> None:
    """For any categories dict with an empty list or empty/whitespace pattern,
    load_category_config SHALL raise ConfigError."""
    toml_content = _categories_to_toml(bad_categories)

    with tempfile.NamedTemporaryFile(
        suffix=".toml", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(toml_content)
        tmp_path = f.name

    try:
        with pytest.raises(ConfigError):
            load_category_config(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Property 2: Substring matching is case-insensitive
# Tag: Feature: criteria-filtering-pdf-export, Property 2: Substring matching is case-insensitive
# Validates: Requirements 1.4
# ---------------------------------------------------------------------------

# Strategy for non-empty text usable as criterion names / patterns
_nonempty_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != "")


@given(name=_nonempty_text, pattern=_nonempty_text)
@settings(max_examples=200)
def test_property_substring_matching_is_case_insensitive(
    name: str,
    pattern: str,
) -> None:
    """For any criterion name and any pattern, matches_any_pattern(name, (pattern,))
    SHALL return True iff pattern.lower() is a substring of name.lower()."""
    expected = pattern.lower() in name.lower()
    assert matches_any_pattern(name, (pattern,)) is expected


# ---------------------------------------------------------------------------
# Strategies for RubricFeedback generation
# ---------------------------------------------------------------------------

_criterion_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters=" -"),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != "")

_criterion = st.builds(
    Criterion,
    name=_criterion_name,
    score=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    feedback=st.text(max_size=50),
)

_rubric_feedback = st.builds(
    RubricFeedback,
    criteria=st.tuples(*[_criterion] * 1).map(tuple)
    | st.lists(_criterion, min_size=0, max_size=8).map(tuple),
)

_patterns_tuple = st.lists(_valid_pattern, min_size=1, max_size=5).map(tuple)


# ---------------------------------------------------------------------------
# Property 3: Filter keeps only matching criteria
# Tag: Feature: criteria-filtering-pdf-export, Property 3: Filter keeps only matching criteria
# Validates: Requirements 2.1, 2.2, 1.5
# ---------------------------------------------------------------------------


@given(rubric=_rubric_feedback, patterns=_patterns_tuple)
@settings(max_examples=200)
def test_property_filter_keeps_only_matching_criteria(
    rubric: RubricFeedback,
    patterns: tuple[str, ...],
) -> None:
    """For any RubricFeedback and any tuple of patterns, every criterion in
    filter_rubric(rubric, patterns) SHALL match at least one pattern (no false
    inclusions), and every criterion in the original rubric that matches at
    least one pattern SHALL appear in the filtered result (no false exclusions)."""
    filtered = filter_rubric(rubric, patterns)

    # No false inclusions: every kept criterion must match
    for criterion in filtered.criteria:
        assert matches_any_pattern(criterion.name, patterns), (
            f"False inclusion: '{criterion.name}' does not match any pattern in {patterns}"
        )

    # No false exclusions: every matching original criterion must be kept
    expected_names = [
        c.name for c in rubric.criteria if matches_any_pattern(c.name, patterns)
    ]
    actual_names = [c.name for c in filtered.criteria]
    assert actual_names == expected_names, (
        f"False exclusion: expected {expected_names}, got {actual_names}"
    )


# ---------------------------------------------------------------------------
# Property 4: Filter preserves criterion order
# Tag: Feature: criteria-filtering-pdf-export, Property 4: Filter preserves criterion order
# Validates: Requirements 2.4
# ---------------------------------------------------------------------------


@given(rubric=_rubric_feedback, patterns=_patterns_tuple)
@settings(max_examples=200)
def test_property_filter_preserves_criterion_order(
    rubric: RubricFeedback,
    patterns: tuple[str, ...],
) -> None:
    """For any RubricFeedback and any tuple of patterns, the criteria in
    filter_rubric(rubric, patterns) SHALL appear in the same relative order
    as in the original rubric.criteria (i.e., the filtered tuple is a
    subsequence of the original)."""
    filtered = filter_rubric(rubric, patterns)

    # Collect the indices of each filtered criterion in the original tuple
    original = rubric.criteria
    filtered_indices: list[int] = []
    for fc in filtered.criteria:
        idx = next(
            i
            for i in range(len(original))
            if original[i] == fc and i not in filtered_indices
        )
        filtered_indices.append(idx)

    # Indices must be strictly increasing — that proves subsequence ordering
    assert filtered_indices == sorted(filtered_indices), (
        f"Order not preserved: indices {filtered_indices} are not strictly increasing"
    )


# ---------------------------------------------------------------------------
# Unit tests for filtering module (Task 2.8)
# ---------------------------------------------------------------------------


class TestLoadCategoryConfigHappyPath:
    """Test load_category_config() with a valid TOML file (Req 1.1, 1.3)."""

    def test_loads_valid_toml(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "categories.toml"
        toml_file.write_text(
            '[categories]\nMIS = ["informatie behoefte", "Dashboard"]\nMAC = ["kostprijs"]\n',
            encoding="utf-8",
        )
        config = load_category_config(str(toml_file))

        assert "MIS" in config.categories
        assert "MAC" in config.categories
        assert config.categories["MIS"] == ("informatie behoefte", "Dashboard")
        assert config.categories["MAC"] == ("kostprijs",)

    def test_loads_real_categories_toml(self) -> None:
        """Load the actual project categories.toml to verify end-to-end parsing."""
        config = load_category_config("categories.toml")

        assert "MIS" in config.categories
        assert "MAC" in config.categories
        assert "KMT" in config.categories
        assert "CAT" in config.categories
        assert len(config.categories["MIS"]) == 7
        assert "Cloud" in config.categories["MIS"]

    def test_missing_file_raises_config_error(self) -> None:
        with pytest.raises(ConfigError, match="not found"):
            load_category_config("/nonexistent/path/categories.toml")

    def test_missing_categories_table_raises_config_error(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "bad.toml"
        toml_file.write_text('[other]\nkey = "value"\n', encoding="utf-8")

        with pytest.raises(ConfigError, match="Missing.*categories"):
            load_category_config(str(toml_file))


class TestGetPatterns:
    """Test get_patterns() with known and unknown categories."""

    def setup_method(self) -> None:
        from brightspace_extractor.filtering import CategoryConfig, get_patterns

        self.get_patterns = get_patterns
        self.config = CategoryConfig(
            categories={
                "MIS": ("informatie behoefte", "Dashboard"),
                "MAC": ("kostprijs", "budget omzet"),
            }
        )

    def test_known_category_returns_patterns(self) -> None:
        patterns = self.get_patterns(self.config, "MIS")
        assert patterns == ("informatie behoefte", "Dashboard")

    def test_case_insensitive_lookup(self) -> None:
        patterns = self.get_patterns(self.config, "mis")
        assert patterns == ("informatie behoefte", "Dashboard")

        patterns = self.get_patterns(self.config, "Mac")
        assert patterns == ("kostprijs", "budget omzet")

    def test_unknown_category_raises_config_error(self) -> None:
        with pytest.raises(ConfigError, match="not found.*Available categories"):
            self.get_patterns(self.config, "UNKNOWN")

    def test_unknown_category_lists_available(self) -> None:
        with pytest.raises(ConfigError, match="MAC.*MIS"):
            self.get_patterns(self.config, "XYZ")


class TestFilterRubricEmptyResult:
    """Test filter_rubric() when filtering removes all criteria (Req 2.2)."""

    def test_no_matching_criteria_returns_empty_tuple(self) -> None:
        rubric = RubricFeedback(
            criteria=(
                Criterion(name="Algebra", score=7.0, feedback="Good"),
                Criterion(name="Geometry", score=8.0, feedback="Great"),
            )
        )
        filtered = filter_rubric(rubric, ("Dashboard", "Cloud"))

        assert filtered.criteria == ()

    def test_empty_rubric_stays_empty(self) -> None:
        rubric = RubricFeedback(criteria=())
        filtered = filter_rubric(rubric, ("anything",))

        assert filtered.criteria == ()


class TestMatchesAnyPatternMultiCategory:
    """Test matches_any_pattern() with multi-category matching (Req 1.5)."""

    def test_criterion_matching_multiple_categories(self) -> None:
        """A criterion name that contains patterns from different categories
        should match each category independently."""
        # "Start CAT/ Adviesrapport" contains both "Start CAT" and "CAT/ Adviesrapport"
        name = "Start CAT/ Adviesrapport analyse"

        cat_patterns = ("Start CAT", "CAT/ Adviesrapport")
        kmt_patterns = ("analyse",)

        assert matches_any_pattern(name, cat_patterns) is True
        assert matches_any_pattern(name, kmt_patterns) is True

    def test_criterion_not_matching_unrelated_category(self) -> None:
        name = "Dashboard in Power BI"

        mis_patterns = ("Dashboard",)
        mac_patterns = ("kostprijs", "budget omzet")

        assert matches_any_pattern(name, mis_patterns) is True
        assert matches_any_pattern(name, mac_patterns) is False
