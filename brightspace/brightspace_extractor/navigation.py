"""Brightspace page navigation — class and assignment routing."""

from playwright.sync_api import Page

from brightspace_extractor.exceptions import NavigationError

_DEFAULT_BASE_URL = "https://dlo.mijnhva.nl"
_NAV_TIMEOUT_MS = 30_000


def _navigate_to(page: Page, url: str, error_context: str) -> None:
    """Navigate to a URL and wait for DOM content to load.

    Raises NavigationError with *error_context* on failure.
    """
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
    except Exception as exc:
        raise NavigationError(f"{error_context}: {exc}") from exc


def navigate_to_home(page: Page, *, base_url: str = _DEFAULT_BASE_URL) -> None:
    """Navigate to the Brightspace homepage (My Courses)."""
    _navigate_to(page, f"{base_url}/d2l/home", "Failed to navigate to Brightspace home")


def navigate_to_class(
    page: Page, class_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the class home page.

    Raises NavigationError if the class page cannot be reached or is not found.
    """
    _navigate_to(
        page,
        f"{base_url}/d2l/home/{class_id}",
        f"Failed to navigate to class {class_id}",
    )
    if class_id not in page.url:
        raise NavigationError(
            f"Class {class_id} not found — "
            "the page did not navigate to the expected URL."
        )


def navigate_to_assignment_submissions(
    page: Page, class_id: str, assignment_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the assignment submissions page within a class.

    Raises NavigationError if the page cannot be reached or the assignment
    is not found.
    """
    url = (
        f"{base_url}/d2l/lms/dropbox/admin/mark/folder_submissions_users.d2l"
        f"?db={assignment_id}&ou={class_id}"
    )
    _navigate_to(
        page,
        url,
        f"Failed to navigate to assignment {assignment_id} in class {class_id}",
    )

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
    """Navigate to the assignment (dropbox) folder list for a class."""
    _navigate_to(
        page,
        f"{base_url}/d2l/lms/dropbox/admin/folders_manage.d2l?ou={class_id}",
        f"Failed to navigate to assignments list for class {class_id}",
    )


def navigate_to_classlist(
    page: Page, class_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the classlist page for a class."""
    _navigate_to(
        page,
        f"{base_url}/d2l/lms/classlist/classlist.d2l?ou={class_id}",
        f"Failed to navigate to classlist for class {class_id}",
    )


def navigate_to_groups(
    page: Page, class_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the groups page for a class."""
    _navigate_to(
        page,
        f"{base_url}/d2l/lms/group/group_list.d2l?ou={class_id}",
        f"Failed to navigate to groups for class {class_id}",
    )


def navigate_to_quizzes(
    page: Page, class_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the quizzes management page for a class."""
    _navigate_to(
        page,
        f"{base_url}/d2l/lms/quizzing/admin/quizzes_manage.d2l?ou={class_id}",
        f"Failed to navigate to quizzes for class {class_id}",
    )


def navigate_to_rubrics(
    page: Page, class_id: str, *, base_url: str = _DEFAULT_BASE_URL
) -> None:
    """Navigate to the rubrics list page for a class."""
    _navigate_to(
        page,
        f"{base_url}/d2l/lp/rubrics/list.d2l?ou={class_id}",
        f"Failed to navigate to rubrics for class {class_id}",
    )
