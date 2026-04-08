"""BeautifulSoup-backed adapter implementing the Playwright Page/Locator interface.

This module provides :class:`ExtractionAdapter` (drop-in for ``Page``) and
:class:`SoupLocator` (drop-in for ``Locator``), allowing the existing extraction
functions in ``extraction.py`` to work on static HTML strings without Playwright.

The CLI continues to use real Playwright objects; the API layer uses this adapter.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag


class SoupLocator:
    """Playwright ``Locator`` interface backed by BeautifulSoup elements."""

    def __init__(
        self,
        elements: list[Tag],
        root: BeautifulSoup | Tag,
        selector: str = "",
    ) -> None:
        self._elements = elements
        self._root = root
        self._selector = selector

    # ------------------------------------------------------------------
    # Core query methods
    # ------------------------------------------------------------------

    def count(self) -> int:
        return len(self._elements)

    def nth(self, index: int) -> SoupLocator:
        el = self._elements[index]
        return SoupLocator([el], el, self._selector)

    @property
    def first(self) -> SoupLocator:
        return self.nth(0)

    def text_content(self) -> str | None:
        if not self._elements:
            return None
        return self._elements[0].get_text()

    def get_attribute(self, name: str) -> str | None:
        if not self._elements:
            return None
        return self._elements[0].get(name)

    def locator(self, selector: str) -> SoupLocator:
        """Find child elements matching *selector* within the current elements."""
        results: list[Tag] = []
        for el in self._elements:
            results.extend(el.select(selector))
        return SoupLocator(results, self._root, selector)

    def filter(self, *, has: SoupLocator | None = None) -> SoupLocator:
        """Filter elements to those containing children matching *has*.

        Mirrors Playwright's ``locator.filter(has=sub_locator)`` — keeps only
        parent elements that have at least one descendant matching the
        sub-locator's original CSS selector.
        """
        if has is None:
            return self
        sub_selector = has._selector
        if not sub_selector:
            return self
        filtered = [
            el for el in self._elements if el.select_one(sub_selector) is not None
        ]
        return SoupLocator(filtered, self._root, self._selector)

    # ------------------------------------------------------------------
    # No-op methods (static HTML needs no waiting or interaction)
    # ------------------------------------------------------------------

    def wait_for(self, **kwargs: object) -> None:  # noqa: ARG002
        pass

    def select_option(self, value: str) -> None:  # noqa: ARG002
        pass


class ExtractionAdapter:
    """Drop-in replacement for Playwright ``Page``, backed by BeautifulSoup.

    Usage::

        adapter = ExtractionAdapter(html_string)
        results = extract_classlist(adapter)
    """

    def __init__(self, html: str) -> None:
        self._soup = BeautifulSoup(html, "html.parser")
        self._url = ""

    # ------------------------------------------------------------------
    # Page interface used by extraction functions
    # ------------------------------------------------------------------

    def locator(self, selector: str) -> SoupLocator:
        elements = self._soup.select(selector)
        return SoupLocator(elements, self._soup, selector)

    @property
    def url(self) -> str:
        return self._url

    # ------------------------------------------------------------------
    # No-op methods (static HTML needs no waiting)
    # ------------------------------------------------------------------

    def wait_for_selector(self, selector: str, **kwargs: object) -> None:  # noqa: ARG002
        pass

    def wait_for_load_state(self, state: str = "", **kwargs: object) -> None:  # noqa: ARG002
        pass

    def wait_for_timeout(self, timeout: int) -> None:  # noqa: ARG002
        pass
