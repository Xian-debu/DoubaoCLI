"""Message actions: copy, like, dislike, regenerate, multi-response mode."""

import time

from playwright.sync_api import Page

from .config import MESSAGE_ACTION_BAR


def _find_action_button(page: Page, action: str):
    """Find the action button on the last assistant message."""
    action_map = {
        "copy":       '[class*="copy"]',
        "like":       '[data-key="like"], [class*="like"]',
        "dislike":    '[data-key="dislike"], [class*="dislike"]',
        "regenerate": '[class*="regenerate"], [class*="redo"], [class*="refresh"]',
    }
    sel = action_map.get(action, "")
    if not sel:
        return None
    return page.locator(sel).first


def copy_response(page: Page) -> bool:
    """Click copy button on the last assistant message. Returns True on success."""
    try:
        btn = _find_action_button(page, "copy")
        if btn.count() > 0:
            btn.click()
            time.sleep(0.3)
            return True
    except Exception:
        pass
    return False


def like_response(page: Page) -> bool:
    """Click the like button on the last assistant message."""
    try:
        btn = _find_action_button(page, "like")
        if btn.count() > 0:
            btn.click()
            time.sleep(0.3)
            return True
    except Exception:
        pass
    return False


def dislike_response(page: Page) -> bool:
    """Click the dislike button on the last assistant message."""
    try:
        btn = _find_action_button(page, "dislike")
        if btn.count() > 0:
            btn.click()
            time.sleep(0.3)
            return True
    except Exception:
        pass
    return False


def regenerate(page: Page, timeout: int = 120) -> bool:
    """Click regenerate button and wait for new response. Returns True on success."""
    try:
        btn = _find_action_button(page, "regenerate")
        if btn.count() > 0:
            btn.click()
            time.sleep(1)
            return True
    except Exception:
        pass
    return False


def get_multi_responses(page: Page) -> list[str]:
    """Extract all responses from multi-response comparison mode.

    When "与回答对比" mode is active, doubao shows 5 parallel answers
    labeled 回答：一 through 回答：五.

    Returns list of response texts. Empty list if not in multi-response mode.
    """
    js = """
    () => {
        const results = [];
        // Look for numbered answer containers
        const containers = document.querySelectorAll('[data-attr="select-mode"]');
        for (const c of containers) {
            const text = c.textContent?.trim();
            if (text && text.length > 10) {
                results.push(text);
            }
        }
        if (results.length === 0) {
            // Fallback: look for 回答： patterns
            const body = document.body.innerText;
            const parts = body.split(/回答[：:][一二三四五六七八九十]/);
            for (let i = 1; i < parts.length; i++) {
                const text = parts[i].trim();
                if (text.length > 10) {
                    results.push(text.substring(0, 1000));
                }
            }
        }
        return results;
    }
    """
    try:
        return page.evaluate(js)
    except Exception:
        return []
