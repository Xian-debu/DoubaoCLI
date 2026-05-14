"""CDP browser connection manager — works with any Chromium-based browser."""

import time
from playwright.sync_api import sync_playwright, Page, Browser
from .config import CDP_URL, ConnectionError, PageNotFoundError, PageInfo, NEW_CHAT_SELECTORS


class CDPManager:
    """Connects to a running Chromium browser via Chrome DevTools Protocol.

    The browser must be launched with --remote-debugging-port.
    Chrome:  chrome  --remote-debugging-port=9222
    Edge:    msedge --remote-debugging-port=9222
    Brave:   brave  --remote-debugging-port=9222

    For automatic browser launch, call CDPManager.ensure_browser() first,
    or use the launcher module directly:
        from .launcher import ensure_cdp
        ensure_cdp()
    """

    def __init__(self, cdp_url: str = CDP_URL):
        self.cdp_url = cdp_url
        self._playwright = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    @staticmethod
    def ensure_browser() -> bool:
        """Auto-launch a Chromium browser with CDP if none is running.

        Returns True if a CDP-enabled browser is ready after the call.
        """
        from .launcher import ensure_cdp
        return ensure_cdp()

    def connect(self) -> bool:
        """Connect to a Chromium browser via CDP. Returns True on success."""
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.connect_over_cdp(
                self.cdp_url, timeout=10000
            )
            return True
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to {self.cdp_url}. "
                "Ensure a Chromium browser is running with --remote-debugging-port. "
                f"Details: {e}"
            ) from e

    # ── Public page management API ─────────────────────────────

    def get_pages(self, url_filter: str | None = "doubao.com") -> list[Page]:
        """Get all pages across all browser contexts, optionally filtered by URL.

        This is the canonical way for external code to enumerate pages
        without accessing _browser directly.
        """
        if not self._browser:
            return []
        pages: list[Page] = []
        for ctx in self._browser.contexts:
            for pg in ctx.pages:
                if url_filter is None or url_filter in pg.url:
                    pages.append(pg)
        return pages

    def find_page(self, url_filter: str = "doubao.com") -> Page | None:
        """Find a page whose URL contains url_filter."""
        if not self._browser:
            return None
        for page in self.get_pages(url_filter=None):
            if url_filter in page.url:
                self._page = page
                return page
        return None

    def ensure_page(self, url_filter: str = "doubao.com/chat",
                    navigate_if_missing: bool = True,
                    timeout: int = 30000) -> Page:
        """Find doubao page or navigate to chat URL."""
        page = self.find_page(url_filter="doubao.com")
        if page:
            self._page = page
            return page

        if not navigate_if_missing:
            raise PageNotFoundError(
                "No doubao.com page found and navigate_if_missing=False"
            )

        if not self._browser:
            raise PageNotFoundError("No browser connection")

        for ctx in self._browser.contexts:
            pages = ctx.pages
            if pages:
                page = pages[0]
                try:
                    page.goto("https://www.doubao.com/chat", timeout=timeout)
                    page.wait_for_load_state("domcontentloaded", timeout=timeout)
                    self._page = page
                    return page
                except Exception as e:
                    raise PageNotFoundError(
                        f"Navigation to doubao.com failed: {e}"
                    ) from e

        for ctx in self._browser.contexts:
            try:
                page = ctx.new_page()
                page.goto("https://www.doubao.com/chat", timeout=timeout)
                self._page = page
                return page
            except Exception as e:
                raise PageNotFoundError(
                    f"Could not create new page: {e}"
                ) from e

        raise PageNotFoundError("No browser contexts available")

    def new_page(self, url: str = "https://www.doubao.com/chat",
                 timeout: int = 15000) -> Page:
        """Create a new browser tab in the first available context.

        Navigates to the given URL and sets the new page as tracked.
        """
        if not self._browser:
            raise ConnectionError("Browser not connected")
        if not self._browser.contexts:
            raise ConnectionError("No browser contexts available")
        ctx = self._browser.contexts[0]
        page = ctx.new_page()
        page.goto(url, timeout=timeout)
        page.wait_for_load_state("domcontentloaded")
        self._page = page
        return page

    def resolve_page(self, new_conversation: bool = False) -> Page | None:
        """Find or create the right page for a chat session.

        Single source of truth for page selection. ChatSession calls this
        and uses the returned Page — it never touches _page or _browser directly.

        Logic:
        1. Collect all doubao pages across all contexts
        2. Auto-cleanup if more than 5 pages exist
        3. If new_conversation: navigate first page to /chat, click button
        4. Otherwise: prefer current tracked page if it's a valid conversation
        5. Otherwise: prefer any page with a conversation ID
        6. Fallback: any doubao page, or ensure_page() if none found
        """
        if not self.connected:
            return None

        doubao_pages = self.get_pages(url_filter="doubao.com")

        if not doubao_pages:
            try:
                return self.ensure_page()
            except Exception:
                return None

        if len(doubao_pages) > 5:
            self.trim_pages(max_pages=5)
            doubao_pages = self.get_pages(url_filter="doubao.com")
            if not doubao_pages:
                try:
                    return self.ensure_page()
                except Exception:
                    return None

        if new_conversation:
            try:
                pg = doubao_pages[0]
                pg.goto("https://www.doubao.com/chat", timeout=15000)
                pg.wait_for_load_state("domcontentloaded")
                time.sleep(2)
                for sel in NEW_CHAT_SELECTORS:
                    try:
                        btn = pg.locator(sel).first
                        if btn.count() > 0:
                            btn.click()
                            time.sleep(2)
                            self._page = pg
                            return pg
                    except Exception:
                        pass
                self._page = pg
                return pg
            except Exception:
                return None

        # Prefer the currently tracked page if it's a specific conversation
        if self._page and "doubao.com" in self._page.url:
            url = self._page.url.rstrip("/")
            if "/chat/" in url and url != "https://www.doubao.com/chat":
                return self._page

        # Prefer pages with a conversation ID (not bare /chat)
        for pg in doubao_pages:
            url = pg.url.rstrip("/")
            if "/chat/" in url and not url.endswith("/chat"):
                self._page = pg
                return pg

        # Fall back to any doubao page (including fresh /chat)
        pg = doubao_pages[0]
        self._page = pg
        return pg

    def get_cookies(self) -> list[dict]:
        """Extract cookies from all browser contexts."""
        if not self._browser:
            return []
        cookies: list[dict] = []
        for ctx in self._browser.contexts:
            cookies.extend(ctx.cookies())
        return cookies

    def list_doubao_pages(self) -> list[PageInfo]:
        """List all doubao.com pages across all contexts."""
        pages = []
        for idx, page in enumerate(self.get_pages(url_filter="doubao.com")):
            conv_id = None
            if "/chat/" in page.url:
                conv_id = page.url.split("/chat/")[-1].split("?")[0]
            pages.append(PageInfo(
                index=idx,
                title=page.title(),
                url=page.url,
                conversation_id=conv_id,
            ))
        return pages

    def close_page(self, index: int = -1, conv_id: str | None = None) -> int:
        """Close doubao page(s).

        Args:
            index: Page index from list_doubao_pages(). -1 means close all except current.
            conv_id: Close page with this conversation ID.
        """
        if not self._browser:
            return 0

        closed = 0
        doubao_pages = [(pg.context, pg) for pg in self.get_pages(url_filter="doubao.com")]

        if index == -1 and conv_id is None:
            keep = self._page
            if keep is None and doubao_pages:
                _, keep = doubao_pages[0]
                self._page = keep
            for ctx, page in doubao_pages:
                if page is keep:
                    continue
                try:
                    page.close()
                    closed += 1
                except Exception:
                    pass
            return closed

        if conv_id:
            for ctx, page in doubao_pages:
                if "/chat/" + conv_id in page.url:
                    try:
                        page.close()
                        closed += 1
                    except Exception:
                        pass
            return closed

        if 0 <= index < len(doubao_pages):
            ctx, page = doubao_pages[index]
            try:
                page.close()
                if page is self._page:
                    self._page = None
                closed = 1
            except Exception:
                pass

        return closed

    @property
    def page_count(self) -> int:
        return len(self.get_pages(url_filter="doubao.com"))

    def trim_pages(self, max_pages: int = 5):
        """Close oldest doubao pages if count exceeds max_pages.

        Keeps the most recent pages. Never closes the current tracking page.
        """
        pages = self.list_doubao_pages()
        if len(pages) <= max_pages:
            return 0

        if self._page is None and pages:
            last = pages[-1]
            self._page = self.find_page(url_filter=f"/chat/{last.conversation_id}")

        closed = 0
        to_close = len(pages) - max_pages
        for p in pages:
            if closed >= to_close:
                break
            if self._page and "/chat/" + (p.conversation_id or "") in self._page.url:
                continue
            self.close_page(index=p.index)
            closed += 1
        return closed

    def new_cdp_session(self, page: Page | None = None):
        """Create a new CDP session for direct protocol access."""
        target_page = page or self._page
        if not target_page:
            raise ConnectionError("No page available for CDP session")
        ctx = target_page.context
        return ctx.new_cdp_session(target_page)

    @property
    def connected(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    @property
    def page(self) -> Page | None:
        return self._page

    def close(self):
        """Clean up CDP connection and Playwright resources."""
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._page = None
        self._playwright = None
