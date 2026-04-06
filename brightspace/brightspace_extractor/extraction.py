"""DOM scraping — extract rubric feedback as raw dicts from Brightspace pages."""

from __future__ import annotations

import logging
from datetime import date

from playwright.sync_api import Page, Locator

logger = logging.getLogger(__name__)

_SUBMISSION_ROW_SELECTOR = "tr.d2l-table-row-selectable, tr[class*='d_ggl']"
_GROUP_NAME_SELECTOR = "th label, td.d_gn a, th a"
_STUDENT_NAMES_SELECTOR = ".ds_i, .d2l-htmlblock p"
_RUBRIC_TABLE_SELECTOR = "table.d_g2, table[class*='rubric']"
_RUBRIC_ROW_SELECTOR = "tr"
_CRITERION_NAME_SELECTOR = "th, td:first-child"
_CRITERION_SCORE_SELECTOR = "td.d_gn, td[class*='score'], td:nth-child(2)"
_CRITERION_FEEDBACK_SELECTOR = "td.d_gf, td[class*='feedback'], td:last-child"
_DATE_SELECTOR = "label small, span.ds_b"


def extract_rubric_for_group(page: Page, group_element: Locator) -> dict | None:
    """Extract rubric criteria (name, score, feedback) for a single group submission.

    Clicks into the group's submission detail page, scrapes the rubric table,
    then navigates back.

    Args:
        page: A Playwright Page on the assignment submissions list.
        group_element: A Locator pointing to the group's row or link.

    Returns:
        A dict with keys ``criteria`` (list of dicts with name/score/feedback),
        or *None* if the rubric could not be extracted.
    """
    try:
        link = group_element.locator("a").first
        if link.count() == 0:
            logger.warning(
                "No clickable link found for group element — skipping rubric extraction."
            )
            return None
        link.click()
        page.wait_for_load_state("domcontentloaded")
    except Exception as exc:
        logger.warning("Failed to navigate into group submission detail: %s", exc)
        return None

    criteria: list[dict] = []
    try:
        rubric_table = page.locator(_RUBRIC_TABLE_SELECTOR)
        if rubric_table.count() == 0:
            logger.warning("No rubric table found on submission detail page.")
            return None

        rows = rubric_table.first.locator(_RUBRIC_ROW_SELECTOR)
        for i in range(rows.count()):
            row = rows.nth(i)
            name_el = row.locator(_CRITERION_NAME_SELECTOR)
            score_el = row.locator(_CRITERION_SCORE_SELECTOR)
            feedback_el = row.locator(_CRITERION_FEEDBACK_SELECTOR)

            name = name_el.first.inner_text().strip() if name_el.count() > 0 else ""
            if not name:
                continue  # skip header or empty rows

            score_text = (
                score_el.first.inner_text().strip() if score_el.count() > 0 else "0"
            )
            try:
                score = float(score_text)
            except ValueError:
                score = 0.0

            feedback = (
                feedback_el.first.inner_text().strip()
                if feedback_el.count() > 0
                else ""
            )

            criteria.append({"name": name, "score": score, "feedback": feedback})
    except Exception as exc:
        logger.warning("Error extracting rubric criteria: %s", exc)
        return None
    finally:
        try:
            page.go_back(wait_until="domcontentloaded")
        except Exception as exc:
            logger.warning("Failed to navigate back after rubric extraction: %s", exc)

    if not criteria:
        return None

    return {"criteria": criteria}


def extract_group_submissions(page: Page) -> list[dict]:
    """Extract all group submissions from the current assignment submissions page.

    Iterates over each group row in the submissions table, extracts the group
    name, student names, submission date, and rubric criteria.

    Args:
        page: A Playwright Page on an assignment submissions page.

    Returns:
        A list of raw dicts, each with keys:
        - ``group_name`` (str)
        - ``students`` (list of str)
        - ``rubric`` (dict with ``criteria`` list) or *None*
        - ``submission_date`` (str, ISO format)
    """
    submissions: list[dict] = []

    rows = page.locator(_SUBMISSION_ROW_SELECTOR)
    row_count = rows.count()
    if row_count == 0:
        logger.warning("No submission rows found on the page.")
        return submissions

    for i in range(row_count):
        row = rows.nth(i)

        # --- group name ---
        group_name_el = row.locator(_GROUP_NAME_SELECTOR)
        if group_name_el.count() == 0:
            logger.warning("Row %d: could not find group name — skipping.", i)
            continue
        group_name = group_name_el.first.inner_text().strip()
        if not group_name:
            logger.warning("Row %d: empty group name — skipping.", i)
            continue

        # --- student names ---
        student_els = row.locator(_STUDENT_NAMES_SELECTOR)
        students: list[str] = []
        for j in range(student_els.count()):
            name = student_els.nth(j).inner_text().strip()
            if name:
                students.append(name)

        # --- submission date ---
        date_el = row.locator(_DATE_SELECTOR)
        submission_date_str = ""
        if date_el.count() > 0:
            submission_date_str = date_el.first.inner_text().strip()

        # Default to today if date cannot be parsed
        try:
            submission_date = (
                date.fromisoformat(submission_date_str)
                if submission_date_str
                else date.today()
            )
        except ValueError:
            logger.warning(
                "Row %d (%s): could not parse date '%s' — defaulting to today.",
                i,
                group_name,
                submission_date_str,
            )
            submission_date = date.today()

        # --- rubric ---
        rubric = extract_rubric_for_group(page, row)
        if rubric is None:
            logger.warning(
                "Group '%s': no rubric feedback found — skipping group.", group_name
            )
            continue

        submissions.append(
            {
                "group_name": group_name,
                "students": students,
                "rubric": rubric,
                "submission_date": submission_date.isoformat(),
            }
        )

    return submissions
