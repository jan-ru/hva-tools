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


class TestCliCategoryValidation:
    """Test --category and --category-config validation (Req 3.1, 3.2, 3.3, 3.4)."""

    def test_category_without_config_exits_code_1(self):
        """--category without --category-config should exit with code 1 (Req 3.3)."""
        with pytest.raises(SystemExit) as exc_info:
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "--category",
                    "MIS",
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        assert exc_info.value.code == 1

    def test_unknown_category_exits_code_1(self, tmp_path):
        """--category with unknown name should exit with code 1 listing available categories (Req 3.4)."""
        config = tmp_path / "categories.toml"
        config.write_text(
            '[categories]\nMIS = ["info"]\nMAC = ["kost"]\n',
            encoding="utf-8",
        )
        with pytest.raises(SystemExit) as exc_info:
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "--category",
                    "NONEXISTENT",
                    "--category-config",
                    str(config),
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        assert exc_info.value.code == 1

    def test_unknown_category_lists_available(self, tmp_path, caplog):
        """Error message for unknown category should list available categories (Req 3.4)."""
        config = tmp_path / "categories.toml"
        config.write_text(
            '[categories]\nMIS = ["info"]\nMAC = ["kost"]\n',
            encoding="utf-8",
        )
        with pytest.raises(SystemExit):
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "--category",
                    "NONEXISTENT",
                    "--category-config",
                    str(config),
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        # The error is logged via logger.error, captured by caplog
        assert "MAC" in caplog.text and "MIS" in caplog.text


class TestCliColWidthsValidation:
    """Test --col-widths validation (Req 5.2, 5.5)."""

    def test_col_widths_too_few_values_exits_code_1(self):
        """--col-widths with fewer than 3 values should exit with code 1 (Req 5.5)."""
        with pytest.raises(SystemExit) as exc_info:
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "--col-widths",
                    "3,1",
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        assert exc_info.value.code == 1

    def test_col_widths_too_many_values_exits_code_1(self):
        """--col-widths with more than 3 values should exit with code 1 (Req 5.5)."""
        with pytest.raises(SystemExit) as exc_info:
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "--col-widths",
                    "3,1,6,2",
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        assert exc_info.value.code == 1

    def test_col_widths_non_numeric_exits_code_1(self):
        """--col-widths with non-numeric values should exit with code 1 (Req 5.5)."""
        with pytest.raises(SystemExit) as exc_info:
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "--col-widths",
                    "a,b,c",
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        assert exc_info.value.code == 1

    def test_col_widths_zero_value_exits_code_1(self):
        """--col-widths with zero value should exit with code 1 (Req 5.5)."""
        with pytest.raises(SystemExit) as exc_info:
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "--col-widths",
                    "3,0,6",
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        assert exc_info.value.code == 1

    def test_col_widths_negative_value_exits_code_1(self):
        """--col-widths with negative value should exit with code 1 (Req 5.5)."""
        with pytest.raises(SystemExit) as exc_info:
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "--col-widths",
                    "3,-1,6",
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        assert exc_info.value.code == 1


class TestCliPdfFlag:
    """Test --pdf flag acceptance (Req 4.1)."""

    def test_pdf_flag_accepted(self):
        """--pdf flag should be accepted without parsing error.

        The command will fail at browser connection, not at argument parsing.
        """
        with pytest.raises(SystemExit) as exc_info:
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "--pdf",
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        # Exit code 1 from connection error — parsing succeeded
        assert exc_info.value.code == 1


class TestCliCombinedParameters:
    """Test combined parameter usage (Req 7.3)."""

    def test_category_pdf_col_widths_accepted(self, tmp_path):
        """--category --pdf --col-widths together should be accepted (Req 7.3).

        The command will fail at browser connection, proving all params parsed OK.
        """
        config = tmp_path / "categories.toml"
        config.write_text(
            '[categories]\nMIS = ["info"]\n',
            encoding="utf-8",
        )
        with pytest.raises(SystemExit) as exc_info:
            app(
                [
                    "extract",
                    "12345",
                    "a1",
                    "--category",
                    "MIS",
                    "--category-config",
                    str(config),
                    "--pdf",
                    "--col-widths",
                    "3,1,6",
                    "--cdp-url",
                    "http://localhost:1",
                ]
            )
        # Exit code 1 from connection error — all parameter parsing succeeded
        assert exc_info.value.code == 1
