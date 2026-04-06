"""Browser connection and authentication verification via Playwright CDP."""

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from brightspace_extractor.exceptions import ConnectionError


def connect_to_browser(cdp_url: str) -> tuple[Browser, BrowserContext, Page]:
    """Connect to an existing browser via Playwright CDP using the sync API.

    Args:
        cdp_url: The CDP endpoint URL (e.g. "http://localhost:9222").

    Returns:
        A tuple of (Browser, BrowserContext, Page) for the connected session.

    Raises:
        ConnectionError: If the CDP endpoint is unreachable.
    """
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp(cdp_url)
    except Exception as exc:
        pw.stop()
        raise ConnectionError(
            f"Failed to connect to browser at {cdp_url}: {exc}"
        ) from exc

    contexts = browser.contexts
    if not contexts:
        browser.close()
        pw.stop()
        raise ConnectionError("No browser contexts found in the connected browser.")

    context = contexts[0]
    pages = context.pages
    if not pages:
        browser.close()
        pw.stop()
        raise ConnectionError("No pages found in the browser context.")

    return browser, context, pages[0]


def verify_authentication(page: Page) -> bool:
    """Check if the Brightspace session is authenticated.

    Looks for the presence of a user-menu dropdown that is only visible
    when logged in.

    Args:
        page: A Playwright Page connected to Brightspace.

    Returns:
        True if authenticated, False otherwise.
    """
    try:
        locator = page.locator(
            "d2l-navigation-main-header .d2l-navigation-header-right d2l-dropdown"
        )
        return locator.count() > 0
    except Exception:
        return False
