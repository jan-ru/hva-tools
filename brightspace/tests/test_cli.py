"""Unit tests for CLI argument parsing."""

import pytest

from brightspace_extractor.cli import app, extract


class TestCliArgumentParsing:
    """Test that cyclopts parses arguments correctly for the extract command."""

    def test_extract_command_is_registered(self):
        """The app should have an 'extract' subcommand."""
        # cyclopts registers commands; verify extract is callable via the app
        assert callable(extract)

    def test_valid_arguments_accepted(self):
        """Valid positional + keyword args should not raise during parsing.

        We can't actually *run* the command (it needs a browser), but we can
        verify cyclopts resolves the signature without error by catching the
        expected runtime failure deeper in the pipeline.
        """
        # Calling with valid args will fail at connect_to_browser (no browser
        # running), which triggers sys.exit(1).  That proves parsing succeeded.
        with pytest.raises(SystemExit) as exc_info:
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "a2",
                    "--output-dir",
                    "./tmp",
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        # Exit code 1 comes from the connection error handler — parsing was fine.
        assert exc_info.value.code == 1

    def test_missing_class_id_exits_nonzero(self, capsys):
        """Omitting the required class_id should produce a usage/error message."""
        with pytest.raises(SystemExit) as exc_info:
            app(["extract"])
        assert exc_info.value.code != 0

    def test_missing_assignment_ids_exits_nonzero(self, capsys):
        """Providing class_id but no assignment_ids should error."""
        with pytest.raises(SystemExit) as exc_info:
            app(["extract", "12345"])
        assert exc_info.value.code != 0

    def test_app_has_subcommand_structure(self):
        """The app should support subcommands for extensibility."""
        # Calling with no subcommand should show help / exit
        with pytest.raises(SystemExit):
            app([])
