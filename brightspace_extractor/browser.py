"""Browser connection and authentication verification via Playwright CDP.

Connects to any Chromium-based browser (Chrome, Edge, Brave, …) that has been
launched with ``--remote-debugging-port``.  Microsoft Edge is the recommended
default for HvA environments.
"""

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from brightspace_extractor.exceptions import ConnectionError


def connect_to_browser(cdp_url: str) -> tuple[Browser, BrowserContext, Page]:
    """Connect to an existing Chromium-based browser via CDP.

    Works with any Chromium-based browser (Edge, Chrome, Brave, …) that was
    started with ``--remote-debugging-port=<port>``.

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
    except Exception:
        pw.stop()
        raise ConnectionError(
            f"Could not connect to a browser at {cdp_url}.\n\n"
            "1. Close ALL browser windows (including background processes in the system tray).\n"
            "   The --remote-debugging-port flag only works if the browser is fully closed first.\n\n"
            "2. Launch the browser with remote debugging enabled:\n\n"
            '   Edge:   & "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" '
            "--remote-debugging-port=9222\n"
            '   Chrome: & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" '
            "--remote-debugging-port=9222\n\n"
            "3. Log in to Brightspace manually, then run this command again.\n\n"
            "Tip: verify the debug port is active by opening http://localhost:9222 in another browser."
        )

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

    # Try to find a Brightspace page (any page on a d2l domain).
    for p in pages:
        if "/d2l/" in p.url:
            return browser, context, p

    # Fall back to the first page if no Brightspace tab is found.
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
        # Check for elements only present when authenticated.  The exact
        # Brightspace web-component names vary across versions, so we try
        # a few common indicators.
        for selector in ("d2l-navigation-main-header", ".d2l-body", "d2l-dropdown"):
            if page.locator(selector).count() > 0:
                return True
        return False
    except Exception:
        return False
