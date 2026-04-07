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


def extract_assignments(page: Page) -> list[dict]:
    """Extract assignment names and IDs from the dropbox folder list page.

    Returns a list of dicts with keys: assignment_id, name.
    """
    assignments: list[dict] = []

    # The dropbox folder list uses alternating row classes d_ggl1 / d_ggl2
    rows = page.locator("tr.d_ggl1, tr.d_ggl2")
    try:
        rows.first.wait_for(timeout=15_000)
    except Exception:
        logger.warning("No assignment rows found on the page.")
        return assignments

    row_count = rows.count()
    logger.info("Found %d assignment row(s).", row_count)

    for i in range(row_count):
        row = rows.nth(i)
        # The assignment name is typically in a link within the first <th> or <td>
        link = row.locator("th a, td a").first
        if link.count() == 0:
            continue

        name = (link.text_content() or "").strip()
        href = link.get_attribute("href") or ""

        # Extract the dropbox folder ID from the href (db=XXXXX parameter)
        assignment_id = ""
        if "db=" in href:
            try:
                assignment_id = href.split("db=")[1].split("&")[0]
            except IndexError:
                pass

        if name and assignment_id:
            assignments.append({"assignment_id": assignment_id, "name": name})

    return assignments


def extract_classlist(page: Page) -> list[dict]:
    """Extract student names and usernames from the classlist page.

    Returns a list of dicts with keys: name, username.
    """
    students: list[dict] = []

    rows = page.locator("tr.d_ggl1, tr.d_ggl2")
    try:
        rows.first.wait_for(timeout=15_000)
    except Exception:
        logger.warning("No classlist rows found on the page.")
        return students

    row_count = rows.count()
    logger.info("Found %d classlist row(s).", row_count)

    for i in range(row_count):
        row = rows.nth(i)
        cells = row.locator("td")
        cell_count = cells.count()
        if cell_count < 2:
            continue

        # Brightspace classlist: first cell has a context menu, second has the name link
        name_link = row.locator("td a.d2l-link")
        if name_link.count() == 0:
            name_link = row.locator("td a")

        name = ""
        if name_link.count() > 0:
            name = (name_link.first.text_content() or "").strip()

        # Username is often in a later cell (varies by Brightspace config)
        username = ""
        if cell_count >= 3:
            username = (cells.nth(2).text_content() or "").strip()

        if name:
            students.append({"name": name, "username": username})

    return students


def extract_groups(page: Page) -> list[dict]:
    """Extract group names, categories, and members from the groups page.

    Returns a list of dicts with keys: group_name, category, members.
    """
    groups: list[dict] = []

    # Groups page has expandable sections per group category
    rows = page.locator("tr.d_ggl1, tr.d_ggl2")
    try:
        rows.first.wait_for(timeout=15_000)
    except Exception:
        logger.warning("No group rows found on the page.")
        return groups

    row_count = rows.count()
    logger.info("Found %d group row(s).", row_count)

    # Track current category from section headers
    current_category = ""

    all_rows = page.locator("table.d_g tr")
    total = all_rows.count()

    for i in range(total):
        row = all_rows.nth(i)

        # Check if this is a category header row
        header = row.locator("th.d_gn, th.d_gh")
        if header.count() > 0:
            text = (header.first.text_content() or "").strip()
            if text:
                current_category = text
            continue

        # Check if this is a data row with group info
        css_class = row.get_attribute("class") or ""
        if "d_ggl1" not in css_class and "d_ggl2" not in css_class:
            continue

        cells = row.locator("td")
        if cells.count() < 2:
            continue

        # First cell or link typically has the group name
        name_el = row.locator("td a, th a").first
        if name_el.count() == 0:
            name_el = cells.first

        group_name = (name_el.text_content() or "").strip()

        # Members are often in a subsequent cell, comma-separated
        members_text = ""
        if cells.count() >= 2:
            members_text = (cells.nth(1).text_content() or "").strip()

        members = (
            tuple(m.strip() for m in members_text.split(",") if m.strip())
            if members_text
            else ()
        )

        if group_name:
            groups.append(
                {
                    "group_name": group_name,
                    "category": current_category,
                    "members": members,
                }
            )

    return groups


def extract_courses(page: Page) -> list[dict]:
    """Extract course names and class IDs from the Brightspace homepage.

    Looks for course card links that point to /d2l/home/{class_id}.

    Returns a list of dicts with keys: class_id, name.
    """
    courses: list[dict] = []

    # Brightspace renders enrolled courses as card widgets or list items
    # linking to /d2l/home/{ou}. Try multiple selectors for different layouts.
    # The "My Courses" widget often uses d2l-enrollment-card or similar components.
    # Fall back to any anchor whose href matches the /d2l/home/DIGITS pattern.
    links = page.locator("a[href*='/d2l/home/']")

    try:
        links.first.wait_for(timeout=15_000)
    except Exception:
        logger.warning("No course links found on the homepage.")
        return courses

    link_count = links.count()
    seen: set[str] = set()

    for i in range(link_count):
        link = links.nth(i)
        href = link.get_attribute("href") or ""
        name = (link.text_content() or "").strip()

        # Extract class_id from /d2l/home/{class_id}
        if "/d2l/home/" not in href:
            continue

        segment = href.split("/d2l/home/")[1].split("?")[0].split("/")[0]
        if not segment.isdigit():
            continue

        class_id = segment

        # Deduplicate (same course may appear in multiple links)
        if class_id in seen:
            continue
        seen.add(class_id)

        # Skip empty names or generic navigation text
        if not name or len(name) > 200:
            name = f"(class {class_id})"

        courses.append({"class_id": class_id, "name": name})

    logger.info("Found %d course(s).", len(courses))
    return courses
