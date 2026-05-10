"""CDP browser connection manager — works with any Chromium-based browser."""

from playwright.sync_api import sync_playwright, Page, Browser
from .config import CDP_URL, ConnectionError, PageNotFoundError, PageInfo


class CDPManager:
    """Connects to a running Chromium browser via Chrome DevTools Protocol.

    The browser must be launched with --remote-debugging-port.
    Chrome:  chrome  --remote-debugging-port=9222
    Edge:    msedge --remote-debugging-port=9222
    Brave:   brave  --remote-debugging-port=9222
    """

    def __init__(self, cdp_url: str = CDP_URL):
        self.cdp_url = cdp_url
        self._playwright = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    def connect(self) -> bool:
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

    def find_page(self, url_filter: str = "doubao.com") -> Page | None:
        if not self._browser:
            return None
        for ctx in self._browser.contexts:
            for page in ctx.pages:
                if url_filter in page.url:
                    self._page = page
                    return page
        return None

    def ensure_page(self, url: str = "https://www.doubao.com/chat",
                    timeout: int = 30000) -> Page:
        page = self.find_page()
        if page:
            self._page = page
            return page
        if not self._browser:
            raise PageNotFoundError("No browser connection")
        for ctx in self._browser.contexts:
            pages = ctx.pages
            if pages:
                pages[0].goto(url, timeout=timeout)
                self._page = pages[0]
                return pages[0]
            try:
                new_page = ctx.new_page()
                new_page.goto(url, timeout=timeout)
                self._page = new_page
                return new_page
            except Exception as e:
                raise PageNotFoundError(str(e)) from e
        raise PageNotFoundError("No browser contexts available")

    def list_doubao_pages(self) -> list[PageInfo]:
        pages = []
        if not self._browser:
            return pages
        for idx, ctx in enumerate(self._browser.contexts):
            for pi, page in enumerate(ctx.pages):
                if "doubao.com" in page.url:
                    conv_id = None
                    if "/chat/" in page.url:
                        conv_id = page.url.split("/chat/")[-1].split("?")[0]
                    pages.append(PageInfo(
                        index=len(pages),
                        title=page.title(),
                        url=page.url,
                        conversation_id=conv_id,
                    ))
        return pages

    def close_page(self, index: int = -1) -> int:
        if not self._browser:
            return 0
        doubao_pages = []
        for ctx in self._browser.contexts:
            for page in ctx.pages:
                if "doubao.com" in page.url:
                    doubao_pages.append((ctx, page))
        if index == -1:
            keep = self._page or (doubao_pages[0][1] if doubao_pages else None)
            closed = 0
            for ctx, page in doubao_pages:
                if page is not keep:
                    try: page.close(); closed += 1
                    except Exception: pass
            return closed
        if 0 <= index < len(doubao_pages):
            doubao_pages[index][1].close()
            return 1
        return 0

    @property
    def page_count(self) -> int:
        return len(self.list_doubao_pages())

    def trim_pages(self, max_pages: int = 5):
        pages = self.list_doubao_pages()
        if len(pages) <= max_pages:
            return 0
        closed = 0
        for p in pages[:len(pages) - max_pages]:
            self.close_page(p.index)
            closed += 1
        return closed

    @property
    def connected(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    @property
    def page(self) -> Page | None:
        return self._page

    def close(self):
        try:
            if self._browser: self._browser.close()
        except Exception: pass
        try:
            if self._playwright: self._playwright.stop()
        except Exception: pass
        self._browser = self._page = self._playwright = None
