#!/usr/bin/env python3
"""
Reusable web scraping utilities for Playwright + BeautifulSoup projects
"""

from __future__ import annotations

import logging
import time
import re
from typing import TYPE_CHECKING, Dict, List, Any, Optional, Tuple

from bs4 import BeautifulSoup

import config

if TYPE_CHECKING:
    from playwright.sync_api import Page, Browser

log = logging.getLogger(__name__)


def _retry(fn, *, retries: int = config.MAX_RETRIES, delay: float = config.RETRY_DELAY_S):
    """Call *fn* up to *retries* times, waiting *delay* seconds between attempts."""
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                log.warning("Attempt %d/%d failed (%s). Retrying in %.1fs…", attempt, retries, exc, delay)
                time.sleep(delay)
    raise last_exc


class BrowserManager:
    """Manages browser connections and page operations"""

    def __init__(self, debug_port: str = config.CHROME_DEBUG_PORT, use_existing_session: bool = True):
        self.debug_port = debug_port
        self.use_existing_session = use_existing_session

    def get_browser_and_page(self) -> Tuple[Optional[Browser], Optional[Page]]:
        """Get browser and page with connection handling"""
        if self.use_existing_session:
            return self._connect_to_existing_session()
        else:
            return self._launch_new_browser()

    def _connect_to_existing_session(self) -> Tuple[Optional[Browser], Optional[Page]]:
        """Connect to existing Chrome session via CDP"""
        from playwright.sync_api import sync_playwright

        try:
            def _connect():
                with sync_playwright() as p:
                    browser = p.chromium.connect_over_cdp(self.debug_port)
                    contexts = browser.contexts
                    if not contexts:
                        raise RuntimeError("No browser contexts found")

                    pages = contexts[0].pages
                    if not pages:
                        raise RuntimeError("No pages found")

                    return browser, pages[0]

            return _retry(_connect)

        except Exception as e:
            log.error("Could not connect to existing session: %s", e)
            return None, None

    def _launch_new_browser(self) -> Tuple[Optional[Browser], Optional[Page]]:
        """Launch new headless browser"""
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                return browser, page
        except Exception as e:
            log.error("Error launching new browser: %s", e)
            return None, None

    def find_page_by_domain(self, pages: List[Page], domain: str) -> Optional[Page]:
        """Find page containing specific domain"""
        for page in pages:
            if domain.lower() in page.url.lower():
                return page
        return None


class SelectorFinder:
    """Utility class for finding DOM elements with fallback selectors"""

    @staticmethod
    def find_by_selectors(page_or_soup, selectors: List[str], method='query_selector'):
        """Try multiple selectors until one works"""
        for selector in selectors:
            try:
                if hasattr(page_or_soup, method):
                    element = getattr(page_or_soup, method)(selector)
                else:
                    element = page_or_soup.find(selector)
                if element:
                    return element
            except Exception:
                continue
        return None

    @staticmethod
    def get_username_selectors() -> List[str]:
        """Common username/email field selectors"""
        return [
            'input[type="email"]',
            'input[name="email"]',
            'input[id*="email"]',
            'input[name="username"]',
            'input[id*="username"]',
            'input[placeholder*="email" i]',
            'input[placeholder*="username" i]'
        ]

    @staticmethod
    def get_password_selectors() -> List[str]:
        """Common password field selectors"""
        return [
            'input[type="password"]',
            'input[name="password"]',
            'input[id*="password"]',
            'input[placeholder*="password" i]'
        ]

    @staticmethod
    def get_login_button_selectors() -> List[str]:
        """Common login button selectors"""
        return [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
            'button:has-text("Inloggen")',
            'button:has-text("Log in")',
            '[role="button"]:has-text("Login")',
            '[role="button"]:has-text("Sign in")'
        ]


class PatternExtractor:
    """Utility class for extracting common data patterns from HTML"""

    @staticmethod
    def extract_time_duration(soup: BeautifulSoup, pattern: str = r'(\d+)\s*uren?\s*en\s*(\d+)\s*minuten?') -> Optional[int]:
        """Extract time duration in minutes from Dutch time format"""
        elements = soup.find_all(attrs={"title": re.compile(pattern)})
        if elements:
            time_text = elements[0]['title']
            match = re.search(pattern, time_text)
            if match:
                hours, minutes = int(match.group(1)), int(match.group(2))
                return hours * 60 + minutes
        return None

    @staticmethod
    def extract_percentage(soup: BeautifulSoup, pattern: str = r'(\d+)%') -> Optional[int]:
        """Extract percentage values from HTML"""
        elements = soup.find_all(attrs={"title": re.compile(pattern)})
        if elements:
            text = elements[0]['title']
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def extract_completion_ratio(soup: BeautifulSoup, item_type: str) -> Tuple[Optional[int], Optional[int], Optional[float]]:
        """Extract X/Y completion ratios (e.g., '5 van de 10 opdrachten')"""
        pattern = rf'(\d+)\s*van de\s*(\d+)\s*{item_type}'
        elements = soup.find_all(attrs={"title": re.compile(pattern)})

        if elements:
            text = elements[0]['title']
            match = re.search(pattern, text)
            if match:
                completed, total = int(match.group(1)), int(match.group(2))
                percentage = (completed / total * 100) if total > 0 else 0
                return completed, total, percentage

        return None, None, None

    @staticmethod
    def extract_select_options(soup: BeautifulSoup, selector: str) -> List[Dict[str, str]]:
        """Extract all options from a select element"""
        select = soup.find('select', id=selector.replace('#', ''))
        options = []

        if select:
            for option in select.find_all('option'):
                value = option.get('value')
                text = option.get_text(strip=True)
                if value and value != "":  # Skip empty options
                    options.append({'value': value, 'name': text})

        return options


class ScrapingSession:
    """High-level scraping session manager"""

    def __init__(self, debug_port: str = config.CHROME_DEBUG_PORT):
        self.browser_manager = BrowserManager(debug_port)
        self.selector_finder = SelectorFinder()
        self.pattern_extractor = PatternExtractor()

    def connect_to_existing_browser(self, domain_hint: str = None) -> Optional[Page]:
        """Connect to existing browser and optionally find page by domain"""
        browser, page = self.browser_manager.get_browser_and_page()
        if not browser or not page:
            return None

        if domain_hint:
            contexts = browser.contexts
            if contexts and contexts[0].pages:
                specific_page = self.browser_manager.find_page_by_domain(contexts[0].pages, domain_hint)
                if specific_page:
                    return specific_page

        return page

    def wait_and_extract(self, page: Page, wait_time: int = 2000) -> BeautifulSoup:
        """Wait for content to load and return a BeautifulSoup object.

        Prefers waiting for the network to be idle (dynamic wait) and falls back
        to a fixed timeout if that is not supported.
        """
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        try:
            page.wait_for_load_state("networkidle", timeout=wait_time * 2)
        except PlaywrightTimeoutError:
            log.debug("networkidle timeout; falling back to fixed %dms wait", wait_time)
            page.wait_for_timeout(wait_time)
        except Exception:
            page.wait_for_timeout(wait_time)

        content = page.content()
        return BeautifulSoup(content, 'html.parser')

    def select_option_and_wait(self, page: Page, selector: str, value: str, wait_time: int = 1000):
        """Select option from dropdown and wait for page update.

        Uses a dynamic network-idle wait after the selection; falls back to a
        fixed timeout if the dynamic wait times out.
        """
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        def _do_select():
            page.select_option(selector, value)

        _retry(_do_select)

        try:
            page.wait_for_load_state("networkidle", timeout=wait_time * 2)
        except PlaywrightTimeoutError:
            log.debug("networkidle timeout after select; falling back to fixed %dms wait", wait_time)
            page.wait_for_timeout(wait_time)
        except Exception:
            page.wait_for_timeout(wait_time)
