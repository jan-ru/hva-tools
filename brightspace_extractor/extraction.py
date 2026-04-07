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

    Finds all submission links (href containing folder_submissions_users.d2l)
    and extracts the assignment name and dropbox folder ID.

    Returns a list of dicts with keys: assignment_id, name.
    """
    assignments: list[dict] = []

    # Each assignment has a link to its submissions page with db=XXXXX
    links = page.locator("a[href*='folder_submissions_users.d2l']")
    try:
        links.first.wait_for(timeout=15_000)
    except Exception:
        logger.warning("No assignment links found on the page.")
        return assignments

    link_count = links.count()
    logger.info("Found %d assignment link(s).", link_count)

    for i in range(link_count):
        link = links.nth(i)
        name = (link.text_content() or "").strip()
        href = link.get_attribute("href") or ""

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
    """Extract student names, org defined IDs, and roles from the classlist page.

    Automatically selects "200 per page" to avoid pagination where possible,
    then scrapes all rows from the d2l-table grid.

    Returns a list of dicts with keys: name, org_defined_id, role.
    """
    students: list[dict] = []

    # Select "200 per page" to minimise pagination
    page_size_select = page.locator("select[name='gridUsers_sl_pgS2']")
    if page_size_select.count() > 0:
        page_size_select.first.select_option("200")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

    # Rows are inside table#z_e; each data row has a th.d_ich with the name
    table = page.locator("table.d2l-table.d_gl")
    if table.count() == 0:
        logger.warning("No classlist table found on the page.")
        return students

    rows = table.locator("tr:has(th.d_ich)")
    try:
        rows.first.wait_for(timeout=15_000)
    except Exception:
        logger.warning("No classlist rows found on the page.")
        return students

    row_count = rows.count()
    logger.info("Found %d classlist row(s).", row_count)

    for i in range(row_count):
        row = rows.nth(i)

        # Name is in th.d_ich > a
        name_el = row.locator("th.d_ich a.d2l-link")
        name = (
            (name_el.first.text_content() or "").strip() if name_el.count() > 0 else ""
        )

        # Org Defined ID and Role are in td.d_gn > label elements
        labels = row.locator("td.d_gn label")
        label_count = labels.count()

        org_defined_id = (
            (labels.nth(0).text_content() or "").strip() if label_count >= 1 else ""
        )
        role = (labels.nth(1).text_content() or "").strip() if label_count >= 2 else ""

        if name:
            students.append(
                {
                    "name": name,
                    "org_defined_id": org_defined_id,
                    "role": role,
                }
            )

    return students


def _scrape_group_table(page: Page) -> list[dict]:
    """Scrape group rows from the currently visible group table.

    Returns list of dicts with keys: group_name, members_enrolled, members_max.
    """
    rows_out: list[dict] = []
    table = page.locator("table.d2l-table.d_gl")
    if table.count() == 0:
        return rows_out

    rows = table.locator("tr:has(th.d_ich)")
    row_count = rows.count()

    for i in range(row_count):
        row = rows.nth(i)
        name_el = row.locator("th.d_ich a.d2l-link")
        group_name = (
            (name_el.first.text_content() or "").strip() if name_el.count() > 0 else ""
        )

        # Members column is the first td.d_gc, shows e.g. "4/4"
        members_cell = row.locator("td.d_gc").first
        members_text = (
            (members_cell.text_content() or "").strip()
            if members_cell.count() > 0
            else ""
        )

        if group_name:
            rows_out.append({"group_name": group_name, "members": members_text})

    return rows_out


def extract_groups(page: Page) -> list[dict]:
    """Extract group names and member counts from the groups page.

    Iterates through all categories in the category dropdown, scraping
    the group table for each one.

    Returns a list of dicts with keys: group_name, category, members.
    """
    groups: list[dict] = []

    # Find the category filter dropdown (d2l-group-section-filter or a <select>)
    # The page uses a custom element; fall back to a regular select
    cat_select = page.locator("select.d2l-select").filter(has=page.locator("option"))

    # Find the select that contains category names (not page-size selects)
    category_select = None
    for i in range(cat_select.count()):
        sel = cat_select.nth(i)
        # Check if any option text looks like a category (not "X per page")
        first_opt = sel.locator("option").first
        text = (first_opt.text_content() or "").strip()
        if "per page" not in text and "of" not in text:
            category_select = sel
            break

    if category_select is None:
        # No category dropdown — try scraping the single visible table
        logger.info("No category dropdown found, scraping visible table.")
        table_rows = _scrape_group_table(page)
        for r in table_rows:
            groups.append({**r, "category": ""})
        return groups

    # Collect all category option values and labels
    options = category_select.locator("option")
    opt_count = options.count()
    categories: list[tuple[str, str]] = []
    for i in range(opt_count):
        opt = options.nth(i)
        value = opt.get_attribute("value") or ""
        label = (opt.text_content() or "").strip()
        if value:
            categories.append((value, label))

    logger.info("Found %d group categor(ies).", len(categories))

    for value, label in categories:
        logger.info("Switching to category: %s", label)
        category_select.select_option(value)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)

        table_rows = _scrape_group_table(page)
        for r in table_rows:
            groups.append({**r, "category": label})

    logger.info("Found %d group(s) total.", len(groups))
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
