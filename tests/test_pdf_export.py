"""Unit tests for the PDF export module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from brightspace_extractor.exceptions import PdfExportError
from brightspace_extractor.pdf_export import (
    check_pandoc_available,
    convert_md_to_pdf,
    export_all_pdfs,
)


class TestCheckPandocAvailable:
    """Tests for check_pandoc_available()."""

    @patch("brightspace_extractor.pdf_export.shutil.which", return_value=None)
    def test_raises_when_pandoc_not_found(self, mock_which: MagicMock) -> None:
        with pytest.raises(PdfExportError, match="pandoc is not installed"):
            check_pandoc_available()
        mock_which.assert_called_once_with("pandoc")

    @patch(
        "brightspace_extractor.pdf_export.shutil.which", return_value="/usr/bin/pandoc"
    )
    def test_does_not_raise_when_pandoc_found(self, mock_which: MagicMock) -> None:
        check_pandoc_available()  # should not raise
        mock_which.assert_called_once_with("pandoc")


class TestConvertMdToPdf:
    """Tests for convert_md_to_pdf()."""

    @patch("brightspace_extractor.pdf_export.subprocess.run")
    def test_constructs_correct_command(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        convert_md_to_pdf("/tmp/input.md", "/tmp/output.pdf")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "pandoc"
        assert "/tmp/input.md" in cmd
        assert "-o" in cmd
        assert "/tmp/output.pdf" in cmd
        assert "--pdf-engine=typst" in cmd

    @patch("brightspace_extractor.pdf_export.subprocess.run")
    def test_includes_default_margins(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        convert_md_to_pdf("/tmp/input.md", "/tmp/output.pdf")
        cmd = mock_run.call_args[0][0]
        assert "-V" in cmd
        assert "margin-top:1.1cm" in cmd
        assert "margin-bottom:1.1cm" in cmd
        assert "margin-left:1.1cm" in cmd
        assert "margin-right:1.1cm" in cmd

    @patch("brightspace_extractor.pdf_export.subprocess.run")
    def test_includes_custom_margins(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        convert_md_to_pdf("/tmp/input.md", "/tmp/output.pdf", margins="2cm")
        cmd = mock_run.call_args[0][0]
        assert "margin-top:2cm" in cmd

    @patch("brightspace_extractor.pdf_export.subprocess.run")
    def test_includes_a4_papersize(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        convert_md_to_pdf("/tmp/input.md", "/tmp/output.pdf")
        cmd = mock_run.call_args[0][0]
        assert "papersize:a4" in cmd

    @patch("brightspace_extractor.pdf_export.subprocess.run")
    def test_raises_on_pandoc_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stderr="some error")
        with pytest.raises(PdfExportError, match="pandoc failed"):
            convert_md_to_pdf("/tmp/input.md", "/tmp/output.pdf")

    @patch("brightspace_extractor.pdf_export.subprocess.run")
    def test_passes_capture_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        convert_md_to_pdf("/tmp/input.md", "/tmp/output.pdf")
        kwargs = mock_run.call_args[1]
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True


class TestExportAllPdfs:
    """Tests for export_all_pdfs()."""

    def test_converts_all_md_files(self, tmp_path: Path) -> None:
        (tmp_path / "group-a.md").write_text("# A")
        (tmp_path / "group-b.md").write_text("# B")
        with patch(
            "brightspace_extractor.pdf_export.convert_md_to_pdf"
        ) as mock_convert:
            success, failure = export_all_pdfs(str(tmp_path))
        assert success == 2
        assert failure == 0
        assert mock_convert.call_count == 2

    def test_pdf_placed_in_same_directory_as_markdown(self, tmp_path: Path) -> None:
        md_file = tmp_path / "group-a.md"
        md_file.write_text("# A")
        with patch(
            "brightspace_extractor.pdf_export.convert_md_to_pdf"
        ) as mock_convert:
            export_all_pdfs(str(tmp_path))
        call_args = mock_convert.call_args[0]
        md_arg = Path(call_args[0])
        pdf_arg = Path(call_args[1])
        assert md_arg.parent == pdf_arg.parent
        assert pdf_arg.suffix == ".pdf"
        assert pdf_arg.stem == md_arg.stem

    def test_continues_on_individual_failure(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("# A")
        (tmp_path / "b.md").write_text("# B")
        (tmp_path / "c.md").write_text("# C")

        call_count = 0

        def side_effect(md_path: str, pdf_path: str, margins: str = "1.1cm") -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise PdfExportError("conversion failed")

        with patch(
            "brightspace_extractor.pdf_export.convert_md_to_pdf",
            side_effect=side_effect,
        ):
            success, failure = export_all_pdfs(str(tmp_path))
        assert success == 2
        assert failure == 1

    def test_returns_zero_counts_for_empty_directory(self, tmp_path: Path) -> None:
        success, failure = export_all_pdfs(str(tmp_path))
        assert success == 0
        assert failure == 0

    def test_logs_warning_on_failure(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        (tmp_path / "fail.md").write_text("# Fail")
        with patch(
            "brightspace_extractor.pdf_export.convert_md_to_pdf",
            side_effect=PdfExportError("bad conversion"),
        ):
            import logging

            with caplog.at_level(logging.WARNING):
                success, failure = export_all_pdfs(str(tmp_path))
        assert failure == 1
        assert "Failed to convert" in caplog.text

    def test_ignores_non_md_files(self, tmp_path: Path) -> None:
        (tmp_path / "group-a.md").write_text("# A")
        (tmp_path / "notes.txt").write_text("not markdown")
        (tmp_path / "data.csv").write_text("a,b,c")
        with patch(
            "brightspace_extractor.pdf_export.convert_md_to_pdf"
        ) as mock_convert:
            success, failure = export_all_pdfs(str(tmp_path))
        assert success == 1
        assert failure == 0
        assert mock_convert.call_count == 1
