"""Unit tests for error handling paths.

Tests cover:
- Authentication failure → error message + exit code 1
- Missing assignment → warning logged, continues processing remaining
- Navigation timeout → error logged, continues processing remaining
- Missing DOM element → warning logged with context, continues processing
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from brightspace_extractor.cli import app
from brightspace_extractor.exceptions import (
    ConnectionError,
    NavigationError,
)


def _make_mock_page() -> MagicMock:
    """Create a mock Playwright Page with sensible defaults."""
    page = MagicMock()
    page.goto = MagicMock()
    page.go_back = MagicMock()
    page.wait_for_load_state = MagicMock()
    return page


# ---------------------------------------------------------------------------
# Authentication failure
# ---------------------------------------------------------------------------


class TestAuthenticationFailure:
    """Req 1.3 — unauthenticated session → error message + exit code 1."""

    @patch("brightspace_extractor.cli.connect_to_browser")
    @patch("brightspace_extractor.cli.verify_authentication", return_value=False)
    def test_auth_failure_exits_with_code_1(self, mock_verify, mock_connect, caplog):
        mock_browser = MagicMock()
        mock_connect.return_value = (mock_browser, MagicMock(), _make_mock_page())

        with pytest.raises(SystemExit) as exc_info:
            app(["extract", "CLS1", "A1", "--cdp-url", "http://localhost:1"])

        assert exc_info.value.code == 1

    @patch("brightspace_extractor.cli.connect_to_browser")
    @patch("brightspace_extractor.cli.verify_authentication", return_value=False)
    def test_auth_failure_logs_error_message(self, mock_verify, mock_connect, caplog):
        mock_browser = MagicMock()
        mock_connect.return_value = (mock_browser, MagicMock(), _make_mock_page())

        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit):
                app(["extract", "CLS1", "A1", "--cdp-url", "http://localhost:1"])

        assert any("not authenticated" in r.message.lower() for r in caplog.records)

    @patch("brightspace_extractor.cli.connect_to_browser")
    @patch("brightspace_extractor.cli.verify_authentication", return_value=False)
    def test_auth_failure_closes_browser(self, mock_verify, mock_connect):
        mock_browser = MagicMock()
        mock_connect.return_value = (mock_browser, MagicMock(), _make_mock_page())

        with pytest.raises(SystemExit):
            app(["extract", "CLS1", "A1", "--cdp-url", "http://localhost:1"])

        mock_browser.close.assert_called_once()


# ---------------------------------------------------------------------------
# Missing assignment — graceful degradation (Req 3.4, 8.1)
# ---------------------------------------------------------------------------


class TestMissingAssignment:
    """Req 3.4 — missing assignment logs warning and continues others."""

    @patch("brightspace_extractor.cli.write_feedback_files", return_value=0)
    @patch("brightspace_extractor.cli.extract_group_submissions", return_value=[])
    @patch("brightspace_extractor.cli.navigate_to_assignment_submissions")
    @patch("brightspace_extractor.cli.navigate_to_class")
    @patch("brightspace_extractor.cli.verify_authentication", return_value=True)
    @patch("brightspace_extractor.cli.connect_to_browser")
    def test_missing_assignment_logs_warning_and_continues(
        self,
        mock_connect,
        mock_verify,
        mock_nav_class,
        mock_nav_assignment,
        mock_extract,
        mock_write,
        caplog,
    ):
        mock_browser = MagicMock()
        mock_connect.return_value = (mock_browser, MagicMock(), _make_mock_page())

        # First assignment raises NavigationError, second succeeds
        mock_nav_assignment.side_effect = [
            NavigationError("Assignment A1 not found in class CLS1"),
            None,
        ]

        with caplog.at_level(logging.WARNING):
            with pytest.raises(SystemExit) as exc_info:
                app(["extract", "CLS1", "A1", "A2", "--cdp-url", "http://localhost:1"])
            assert exc_info.value.code == 0

        # Warning was logged for the missing assignment
        assert any(
            "A1" in r.message for r in caplog.records if r.levelno == logging.WARNING
        )
        # Second assignment was still processed (extract was called)
        mock_extract.assert_called_once()

    @patch("brightspace_extractor.cli.write_feedback_files", return_value=0)
    @patch("brightspace_extractor.cli.navigate_to_assignment_submissions")
    @patch("brightspace_extractor.cli.navigate_to_class")
    @patch("brightspace_extractor.cli.verify_authentication", return_value=True)
    @patch("brightspace_extractor.cli.connect_to_browser")
    def test_all_assignments_missing_still_completes(
        self,
        mock_connect,
        mock_verify,
        mock_nav_class,
        mock_nav_assignment,
        mock_write,
        caplog,
    ):
        mock_browser = MagicMock()
        mock_connect.return_value = (mock_browser, MagicMock(), _make_mock_page())

        mock_nav_assignment.side_effect = NavigationError("not found")

        # Should not crash — completes successfully (cyclopts calls sys.exit(0))
        with pytest.raises(SystemExit) as exc_info:
            app(["extract", "CLS1", "A1", "A2", "--cdp-url", "http://localhost:1"])
        assert exc_info.value.code == 0

        # write_feedback_files still called (with empty aggregation)
        mock_write.assert_called_once()


# ---------------------------------------------------------------------------
# Navigation timeout — graceful degradation (Req 8.1)
# ---------------------------------------------------------------------------


class TestNavigationTimeout:
    """Req 8.1 — page navigation timeout logs error and continues."""

    @patch("brightspace_extractor.cli.write_feedback_files", return_value=0)
    @patch("brightspace_extractor.cli.extract_group_submissions", return_value=[])
    @patch("brightspace_extractor.cli.navigate_to_assignment_submissions")
    @patch("brightspace_extractor.cli.navigate_to_class")
    @patch("brightspace_extractor.cli.verify_authentication", return_value=True)
    @patch("brightspace_extractor.cli.connect_to_browser")
    def test_timeout_on_one_assignment_continues_to_next(
        self,
        mock_connect,
        mock_verify,
        mock_nav_class,
        mock_nav_assignment,
        mock_extract,
        mock_write,
        caplog,
    ):
        mock_browser = MagicMock()
        mock_connect.return_value = (mock_browser, MagicMock(), _make_mock_page())

        # Simulate a timeout on the first assignment (NavigationError wraps it)
        mock_nav_assignment.side_effect = [
            NavigationError(
                "Failed to navigate to assignment A1 in class CLS1: Timeout 30000ms exceeded"
            ),
            None,  # second assignment succeeds
        ]

        with caplog.at_level(logging.WARNING):
            with pytest.raises(SystemExit) as exc_info:
                app(["extract", "CLS1", "A1", "A2", "--cdp-url", "http://localhost:1"])
            assert exc_info.value.code == 0

        assert any("A1" in r.message for r in caplog.records)
        # Second assignment was still processed
        mock_extract.assert_called_once()


# ---------------------------------------------------------------------------
# Missing DOM element — warning with context (Req 8.2)
# ---------------------------------------------------------------------------


class TestMissingDomElement:
    """Req 8.2 — missing DOM element logs warning with context and continues."""

    def test_extract_rubric_missing_link_logs_warning(self, caplog):
        """When the evaluation page has no d2l-rubric element, a warning is logged."""
        from brightspace_extractor.extraction import _extract_rubric_via_api

        page = _make_mock_page()

        # No d2l-rubric element on the page
        rubric_locator = MagicMock()
        rubric_locator.count.return_value = 0
        page.locator.return_value = rubric_locator

        with caplog.at_level(logging.WARNING):
            result = _extract_rubric_via_api(page)

        assert result is None
        assert any("no d2l-rubric" in r.message.lower() for r in caplog.records)

    def test_extract_rubric_no_rubric_table_logs_warning(self, caplog):
        """When the API returns no criteria, a warning is logged."""
        from brightspace_extractor.extraction import _extract_rubric_via_api

        page = _make_mock_page()

        # d2l-rubric element exists but evaluate returns empty criteria
        rubric_locator = MagicMock()
        rubric_locator.count.return_value = 1
        first_el = MagicMock()
        first_el.evaluate.return_value = {"criteria": []}
        rubric_locator.first = first_el
        page.locator.return_value = rubric_locator

        result = _extract_rubric_via_api(page)
        assert result is None

    def test_extract_group_submissions_missing_group_name_skips_row(self, caplog):
        """When no group rows have eval links, no submissions are returned."""
        from brightspace_extractor.extraction import extract_group_submissions

        page = _make_mock_page()

        # Simulate one submission row with no eval link
        row = MagicMock()
        rows_locator = MagicMock()
        rows_locator.count.return_value = 1
        rows_locator.nth.return_value = row

        # The row's eval link locator returns 0 matches
        eval_link_locator = MagicMock()
        eval_link_locator.count.return_value = 0
        row.locator.return_value = eval_link_locator

        page.locator.return_value = rows_locator

        with caplog.at_level(logging.INFO):
            result = extract_group_submissions(page)

        assert result == []

    def test_extract_group_submissions_no_rows_logs_warning(self, caplog):
        """When the submissions page has no rows at all, a warning is logged."""
        from brightspace_extractor.extraction import extract_group_submissions

        page = _make_mock_page()

        rows_locator = MagicMock()
        rows_locator.count.return_value = 0
        page.locator.return_value = rows_locator

        with caplog.at_level(logging.WARNING):
            result = extract_group_submissions(page)

        assert result == []
        assert any("no submission rows" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Connection failure (Req 8.3)
# ---------------------------------------------------------------------------


class TestConnectionFailure:
    """Connection errors produce error message + exit code 1."""

    @patch("brightspace_extractor.cli.connect_to_browser")
    def test_connection_failure_exits_with_code_1(self, mock_connect, caplog):
        mock_connect.side_effect = ConnectionError(
            "Failed to connect to browser at http://localhost:1"
        )

        with pytest.raises(SystemExit) as exc_info:
            app(["extract", "CLS1", "A1", "--cdp-url", "http://localhost:1"])

        assert exc_info.value.code == 1

    @patch("brightspace_extractor.cli.connect_to_browser")
    def test_connection_failure_logs_error(self, mock_connect, caplog):
        mock_connect.side_effect = ConnectionError(
            "Failed to connect to browser at http://localhost:1"
        )

        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit):
                app(["extract", "CLS1", "A1", "--cdp-url", "http://localhost:1"])

        assert any("failed to connect" in r.message.lower() for r in caplog.records)
