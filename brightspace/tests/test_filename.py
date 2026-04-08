"""Property tests for filename derivation."""

from hypothesis import given, settings
from hypothesis import strategies as st

from brightspace_extractor.serialization import group_to_filename

# ---------------------------------------------------------------------------
# Property 4: Filename derivation produces lowercase hyphenated names
# ---------------------------------------------------------------------------


@given(name=st.text(min_size=1, max_size=50))
@settings(max_examples=100)
def test_filename_is_lowercase_no_spaces_md_extension(name: str) -> None:
    """Feature: brightspace-feedback-extractor, Property 4: Filename derivation produces lowercase hyphenated names"""
    result = group_to_filename(name)

    assert result == result.lower(), f"Filename not lowercase: {result}"
    assert " " not in result, f"Filename contains spaces: {result}"
    assert result.endswith(".md"), f"Filename does not end with .md: {result}"


# ---------------------------------------------------------------------------
# Unit tests for known inputs
# ---------------------------------------------------------------------------


class TestGroupToFilename:
    """Unit tests for group_to_filename (Req 6.7)."""

    def test_simple_name(self) -> None:
        assert group_to_filename("Team Alpha") == "team-alpha.md"

    def test_already_lowercase(self) -> None:
        assert group_to_filename("delta") == "delta.md"

    def test_multiple_spaces(self) -> None:
        assert group_to_filename("My Cool Team") == "my-cool-team.md"

    def test_single_word(self) -> None:
        assert group_to_filename("Solo") == "solo.md"

    def test_mixed_case(self) -> None:
        assert group_to_filename("AlPhA BeTa") == "alpha-beta.md"
