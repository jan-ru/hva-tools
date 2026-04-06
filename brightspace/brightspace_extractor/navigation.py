"""Brightspace page navigation — class and assignment routing."""

from playwright.sync_api import Page

from brightspace_extractor.exceptions import NavigationError

# Brightspace URL patterns
_CLASS_HOME_URL = "https://brightspace.ru.nl/d2l/home/{class_id}"
_ASSIGNMENT_SUBMISSIONS_URL = (
    "https://brightspace.ru.nl/d2l/lms/dropbox/admin/folders_manage.d2l"
    "?ou={class_id}&db={assignment_id}"
)

_NAV_TIMEOUT_MS = 30_000


def navigate_to_class(page: Page, class_id: str) -> None:
    """Navigate to the class page using the class identifier.

    Args:
        page: A Playwright Page connected to Brightspace.
        class_id: The Brightspace class (org unit) identifier.

    Raises:
        NavigationError: If the class page cannot be reached or is not found.
    """
    url = _CLASS_HOME_URL.format(class_id=class_id)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
    except Exception as exc:
        raise NavigationError(f"Failed to navigate to class {class_id}: {exc}") from exc

    # Brightspace redirects to a generic "not found" or error page when the
    # class ID is invalid.  Detect this by checking for the course homepage
    # banner that is only present on a valid class page.
    if page.locator("d2l-organization-homepage-header").count() == 0:
        raise NavigationError(
            f"Class {class_id} not found — the page did not contain a valid class header."
        )


def navigate_to_assignment_submissions(
    page: Page, class_id: str, assignment_id: str
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
    url = _ASSIGNMENT_SUBMISSIONS_URL.format(
        class_id=class_id, assignment_id=assignment_id
    )
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
    except Exception as exc:
        raise NavigationError(
            f"Failed to navigate to assignment {assignment_id} in class {class_id}: {exc}"
        ) from exc

    # If the assignment ID is invalid, Brightspace typically shows an error
    # banner or redirects.  Check for the submissions table as a positive
    # indicator that we landed on the right page.
    if page.locator(".d2l-datalist, .d2l-table").count() == 0:
        raise NavigationError(
            f"Assignment {assignment_id} not found in class {class_id} — "
            "no submissions table detected on the page."
        )
