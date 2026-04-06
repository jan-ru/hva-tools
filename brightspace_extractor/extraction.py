"""Extract rubric feedback from Brightspace via the Hypermedia API.

Instead of scraping the DOM directly, this module navigates to each group's
evaluation page, locates the ``d2l-rubric`` web component, and uses its
``assessment-href`` + auth token to call the Brightspace Assessments API.
This is far more reliable than parsing the rendered HTML.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Page

logger = logging.getLogger(__name__)

_GROUP_ROW_SELECTOR = "tr.d_ggl2"
_EVAL_LINK_TITLE_PREFIX = "Go to Evaluation for "


_RUBRIC_EXTRACT_JS = """async (el) => {
    const token = typeof el.token === 'function' ? await el.token() : el.token;
    const headers = token ? {'Authorization': 'Bearer ' + token} : {};
    const assessmentHref = el.getAttribute('assessment-href');
    if (!assessmentHref) return null;

    async function apiFetch(url) {
        const resp = await fetch(url, {headers, credentials: 'same-origin'});
        return await resp.json();
    }

    const assessment = await apiFetch(assessmentHref);
    const criteria = [];

    for (const entity of assessment.entities || []) {
        if (!entity.class?.includes('criterion-assessment-links')) continue;

        const defLink = entity.links?.find(l =>
            l.rel.includes('https://rubrics.api.brightspace.com/rels/criterion'));
        const assessLink = entity.links?.find(l =>
            l.rel.includes('https://assessments.api.brightspace.com/rels/assessment-criterion'));
        if (!defLink || !assessLink) continue;

        const [criterionDef, criterionAssess] = await Promise.all([
            apiFetch(defLink.href), apiFetch(assessLink.href)
        ]);

        const name = criterionDef.properties?.name || 'Unknown';
        const selectedCell = criterionAssess.entities?.find(e =>
            e.class?.includes('selected') && e.class?.includes('assessment-criterion-cell'));
        const score = selectedCell?.properties?.score ?? criterionAssess.properties?.score ?? 0;

        const fbEntity = criterionAssess.entities?.find(e =>
            e.class?.includes('feedback') && e.class?.includes('richtext'));
        let feedback = fbEntity?.properties?.text || '';
        if (selectedCell) {
            const cellFb = selectedCell.entities?.find(e =>
                e.class?.includes('feedback') && e.class?.includes('richtext'));
            if (cellFb?.properties?.text) feedback = cellFb.properties.text;
        }

        criteria.push({name, score, feedback});
    }

    return {
        activityName: assessment.properties?.activityName || '',
        totalScore: assessment.properties?.score || 0,
        criteria
    };
}"""


def _extract_rubric_via_api(page: Page) -> dict | None:
    """Extract rubric data from the current evaluation page via the API.

    Expects the page to be on an evaluation page containing a ``d2l-rubric``
    web component.

    Returns a dict with ``criteria`` list, or *None* on failure.
    """
    rubric_el = page.locator("d2l-rubric")
    if rubric_el.count() == 0:
        logger.warning("No d2l-rubric element found on evaluation page.")
        return None

    try:
        data = rubric_el.first.evaluate(_RUBRIC_EXTRACT_JS)
    except Exception as exc:
        logger.warning("Failed to extract rubric via API: %s", exc)
        return None

    if not data or not data.get("criteria"):
        return None

    return {"criteria": data["criteria"]}


def extract_group_submissions(page: Page) -> list[dict]:
    """Extract all group submissions from the current assignment submissions page.

    For each group row, navigates to the evaluation page, extracts rubric
    data via the Brightspace API, then navigates back.

    Returns a list of dicts with keys: group_name, students, rubric, submission_date.
    """
    submissions: list[dict] = []

    # Ensure group rows are loaded
    logger.info("Extracting from page: %s", page.url)
    try:
        page.wait_for_selector(_GROUP_ROW_SELECTOR, timeout=15_000)
    except Exception:
        logger.warning("Timed out waiting for group rows on %s", page.url)

    rows = page.locator(_GROUP_ROW_SELECTOR)
    row_count = rows.count()
    logger.info("Found %d group row(s) on page.", row_count)
    if row_count == 0:
        logger.warning("No submission rows found on the page.")
        return submissions

    # Collect group names and eval link titles first (DOM changes on navigation)
    groups: list[str] = []
    for i in range(row_count):
        row = rows.nth(i)
        link = row.locator(f"a[title^='{_EVAL_LINK_TITLE_PREFIX}']")
        if link.count() == 0:
            continue
        title = link.first.get_attribute("title") or ""
        group_name = title.removeprefix(_EVAL_LINK_TITLE_PREFIX).strip()
        if group_name:
            groups.append(group_name)

    logger.info("Found %d group(s) to process.", len(groups))

    for group_name in groups:
        logger.info("Processing group: %s", group_name)
        eval_link = page.locator(f"a[title='Go to Evaluation for {group_name}']")
        if eval_link.count() == 0:
            logger.warning("Could not find eval link for '%s' — skipping.", group_name)
            continue

        try:
            eval_link.first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
        except Exception as exc:
            logger.warning(
                "Failed to navigate to evaluation for '%s': %s", group_name, exc
            )
            continue

        rubric = _extract_rubric_via_api(page)

        # Navigate back to submissions list
        try:
            page.go_back(wait_until="networkidle")
            page.wait_for_timeout(2000)
        except Exception as exc:
            logger.warning("Failed to navigate back after '%s': %s", group_name, exc)

        if rubric is None:
            logger.warning(
                "Group '%s': no rubric feedback found — skipping.", group_name
            )
            continue

        submissions.append(
            {
                "group_name": group_name,
                "students": [],
                "rubric": rubric,
                "submission_date": "",
            }
        )

    return submissions
