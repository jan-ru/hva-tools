"""PDF export via pandoc + typst for the Brightspace Feedback Extractor."""

import logging
import shutil
import subprocess
from pathlib import Path

from brightspace_extractor.exceptions import PdfExportError

logger = logging.getLogger(__name__)


def check_pandoc_available() -> None:
    """Verify pandoc is on PATH. Raises PdfExportError if not found."""
    if shutil.which("pandoc") is None:
        raise PdfExportError(
            "pandoc is not installed or not found on PATH. "
            "Install pandoc (https://pandoc.org/installing.html) and ensure it is on your PATH."
        )


def convert_md_to_pdf(
    md_path: str,
    pdf_path: str,
    margins: str = "1.1cm",
) -> None:
    """Convert a single markdown file to PDF using pandoc + typst.

    Raises PdfExportError on pandoc failure.
    """
    cmd = [
        "pandoc",
        md_path,
        "-o",
        pdf_path,
        "--pdf-engine=typst",
        "-V",
        f"margin-top:{margins}",
        "-V",
        f"margin-bottom:{margins}",
        "-V",
        f"margin-left:{margins}",
        "-V",
        f"margin-right:{margins}",
        "-V",
        "papersize:a4",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise PdfExportError(f"pandoc failed for {md_path}: {result.stderr.strip()}")


def export_all_pdfs(
    md_dir: str,
    margins: str = "1.1cm",
) -> tuple[int, int]:
    """Convert all .md files in md_dir to PDF.

    Returns (success_count, failure_count).
    Logs warnings for individual failures but continues processing.
    """
    md_files = sorted(Path(md_dir).glob("*.md"))
    success = 0
    failure = 0

    for md_file in md_files:
        pdf_file = md_file.with_suffix(".pdf")
        try:
            convert_md_to_pdf(str(md_file), str(pdf_file), margins=margins)
            success += 1
        except PdfExportError as exc:
            logger.warning("Failed to convert %s to PDF: %s", md_file.name, exc)
            failure += 1

    return success, failure


def export_combined_pdf(
    md_dir: str,
    output_filename: str = "combined.pdf",
    margins: str = "1.1cm",
) -> None:
    """Concatenate all .md files in md_dir into a single PDF.

    Passes all markdown files to a single pandoc invocation so they are
    rendered as one continuous document.

    Raises PdfExportError on pandoc failure.
    """
    md_files = sorted(Path(md_dir).glob("*.md"))
    if not md_files:
        logger.warning("No markdown files found in %s for combined PDF.", md_dir)
        return

    pdf_path = str(Path(md_dir) / output_filename)
    cmd = [
        "pandoc",
        *[str(f) for f in md_files],
        "-o",
        pdf_path,
        "--pdf-engine=typst",
        "-V",
        f"margin-top:{margins}",
        "-V",
        f"margin-bottom:{margins}",
        "-V",
        f"margin-left:{margins}",
        "-V",
        f"margin-right:{margins}",
        "-V",
        "papersize:a4",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise PdfExportError(f"pandoc failed for combined PDF: {result.stderr.strip()}")

    logger.info("Combined PDF written to %s", pdf_path)
