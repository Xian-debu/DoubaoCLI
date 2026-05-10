"""Deep Think and Web Search support for Doubao.

Both features are built into 超能模式 (Super Mode), not standalone toggles.
Switching to 超能模式 activates: deep reasoning, multi-round search,
browser operations, and web browsing capabilities.

This module provides:
- Super mode activation (which enables deep think + web search)
- Thinking process extraction from responses
- Search source extraction from responses
"""

import time

from playwright.sync_api import Page

from .config import THINKING_INDICATORS, SEARCH_SOURCE_INDICATORS


def enable(page: Page) -> bool:
    """Enable deep think + web search by switching to 超能模式.

    Returns True if mode was activated.
    """
    try:
        chip = page.locator('text=超能模式').first
        if chip.count() > 0:
            chip.click()
            time.sleep(1.5)
            _dismiss_onboarding(page)
            return True
    except Exception:
        pass
    return False


def disable(page: Page) -> bool:
    """Disable deep think by switching back to 快速 mode.

    Returns True if mode was deactivated.
    """
    try:
        chip = page.locator('text=快速').first
        if chip.count() > 0:
            chip.click()
            time.sleep(1)
            return True
    except Exception:
        pass
    return False


def is_enabled(page: Page) -> bool:
    """Check if 超能模式 is active."""
    try:
        chip = page.locator('text=超能模式').first
        if chip.count() > 0:
            parent = chip.locator("..").first
            cls = (parent.get_attribute("class") or "") + (chip.get_attribute("class") or "")
            return "active" in cls or "selected" in cls
    except Exception:
        pass
    return False


def get_thinking_process(page: Page) -> str | None:
    """Extract thinking/reasoning content from 超能模式 response.

    In 超能模式, responses may include a collapsible thinking section
    showing the model's reasoning process.

    Returns the thinking text or None if not found.
    """
    js = """
    () => {
        // Look for thinking section containers
        for (const sel of ['[class*="thinking"]', '[class*="reasoning"]',
                            '[class*="thought"]', 'details summary']) {
            const el = document.querySelector(sel);
            if (el && el.textContent.trim().length > 10) {
                // If it's a details/summary, get the full content
                const parent = el.closest('details');
                return parent ? parent.textContent.trim() : el.textContent.trim();
            }
        }
        // Check for sections with "思考" or "推理" headers
        const allHeaders = document.querySelectorAll('*');
        for (const h of allHeaders) {
            const text = h.textContent?.trim() || '';
            if ((text.includes('思考过程') || text.includes('推理过程')
                 || text.includes('深度思考')) && text.length < 30) {
                const container = h.closest('[class*="container"], div');
                if (container) return container.textContent.trim();
            }
        }
        return null;
    }
    """
    try:
        return page.evaluate(js)
    except Exception:
        return None


def get_search_sources(page: Page) -> list[dict]:
    """Extract web search sources from 超能模式 response.

    Returns list of {title, url} dicts.
    """
    js = """
    () => {
        const sources = [];
        // Look for source/reference links
        for (const sel of ['[class*="source"] a', '[class*="reference"] a',
                            '[class*="citation"] a', 'a[href*="http"]']) {
            const links = document.querySelectorAll(sel);
            for (const link of links) {
                const href = link.getAttribute('href');
                const text = link.textContent.trim();
                if (href && href.startsWith('http') && text) {
                    sources.push({title: text.substring(0, 100), url: href});
                }
            }
        }
        // Also parse "参考 X 篇资料" sections
        const body = document.body.innerText;
        const refMatch = body.match(/参考\\s*(\\d+)\\s*篇资料([\\s\\S]*?)(?=\\n[^\\n]*?\\n|$)/);
        if (refMatch && sources.length === 0) {
            // Sources may be inline links in a reference section
            const allLinks = document.querySelectorAll('a[href*="http"]');
            for (const link of allLinks) {
                const href = link.getAttribute('href');
                const text = link.textContent.trim();
                if (href && text && href.startsWith('http') && text.length > 3) {
                    sources.push({title: text.substring(0, 100), url: href});
                }
            }
        }
        return sources.slice(0, 10);
    }
    """
    try:
        return page.evaluate(js)
    except Exception:
        return []


def _dismiss_onboarding(page: Page):
    """Dismiss the 超能模式 onboarding dialog if present."""
    try:
        dialog = page.locator('[role="dialog"]:has-text("超能模式")').first
        if dialog.count() > 0 and dialog.is_visible():
            close_btn = dialog.locator(
                'button:has-text("开始使用"), button:has-text("知道了"), '
                'button:has-text("关闭"), [class*="close"]'
            ).first
            if close_btn.count() > 0:
                close_btn.click()
            else:
                page.keyboard.press("Escape")
            time.sleep(0.5)
    except Exception:
        pass
