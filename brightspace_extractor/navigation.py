"""Brightspace page navigation — class and assignment routing."""

from playwright.sync_api import Page

from brightspace_extractor.exceptions import NavigationError

_DEFAULT_BASE_URL = "https://dlo.mijnhva.nl"
_NAV_TIMEOUT_MS = 30_000


def _class_home_url(base_url: str, class_id: str) -> str:
    return f"{base_url}/d2l/home/{class_id}"


def navigate_to_home(page: Page, *, base_url: str = _DEFAULT_BASE_URL) -> None:
    """Navigate to the Brightspace homepage (My Courses).

    Raises NavigationError if the page cannot be reached.
    """
    url = f"{base_url}/d2l/home"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
    except Exception as exc:
        raise NavigationError(f"Failed to navigate to Brightspace home: {exc}") from exc


def _assignment_submissions_url(
    base_url: str, class_id: str, assignment_id: str
) -> str:
    return (
        f"{base_url}/d2l/lms/dropbox/admin/mark/folder_submissions_users.d2l"
        f"?db={assignment_id}&ou={class_id}"
    )


def navigate_to_class(
    page: Page, class_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the class page using the class identifier.

    Args:
        page: A Playwright Page connected to Brightspace.
        class_id: The Brightspace class (org unit) identifier.

    Raises:
        NavigationError: If the class page cannot be reached or is not found.
    """
    url = _class_home_url(base_url, class_id)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
    except Exception as exc:
        raise NavigationError(f"Failed to navigate to class {class_id}: {exc}") from exc

    if class_id not in page.url:
        raise NavigationError(
            f"Class {class_id} not found — the page did not navigate to the expected URL."
        )


def navigate_to_assignment_submissions(
    page: Page, class_id: str, assignment_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the assignment submissions page within a class.

    Args:
        page: A Playwright Page connected to Brightspace.
        class_id: The Brightspace class (org unit) identifier.
        assignment_id: The assignment (dropbox folder) identifier.

    Raises:
        NavigationError: If the assignment submissions page cannot be reached
            or the assignment is not found.
    """
    url = _assignment_submissions_url(base_url, class_id, assignment_id)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
    except Exception as exc:
        raise NavigationError(
            f"Failed to navigate to assignment {assignment_id} in class {class_id}: {exc}"
        ) from exc

    # Wait for the group rows to appear (they load after initial DOM).
    try:
        page.wait_for_selector("tr.d_ggl2", timeout=15_000)
    except Exception:
        pass

    if page.locator("tr.d_ggl2").count() == 0:
        raise NavigationError(
            f"Assignment {assignment_id} not found in class {class_id} — "
            "no submissions detected on the page."
        )


def navigate_to_dropbox_list(
    page: Page, class_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the assignment (dropbox) folder list for a class.

    Raises NavigationError if the page cannot be reached.
    """
    url = f"{base_url}/d2l/lms/dropbox/admin/folders_manage.d2l?ou={class_id}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
    except Exception as exc:
        raise NavigationError(
            f"Failed to navigate to assignments list for class {class_id}: {exc}"
        ) from exc


def navigate_to_classlist(
    page: Page, class_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the classlist page for a class.

    Raises NavigationError if the page cannot be reached.
    """
    url = f"{base_url}/d2l/lms/classlist/admin/classlist.d2l?ou={class_id}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
    except Exception as exc:
        raise NavigationError(
            f"Failed to navigate to classlist for class {class_id}: {exc}"
        ) from exc


def navigate_to_groups(
    page: Page, class_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the groups page for a class.

    Raises NavigationError if the page cannot be reached.
    """
    url = f"{base_url}/d2l/lms/group/group_list.d2l?ou={class_id}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
    except Exception as exc:
        raise NavigationError(
            f"Failed to navigate to groups for class {class_id}: {exc}"
        ) from exc
