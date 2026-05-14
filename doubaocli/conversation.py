"""Conversation management: list, open, delete, rename."""

import time

from playwright.sync_api import Page

from .config import (
    CONV_ITEM_CLASS,
    CONV_ACTIVE_CLASS,
    ConversationSummary,
)


def list_conversations(page: Page, limit: int = 20) -> list[ConversationSummary]:
    """Extract conversation list from the sidebar.

    Uses the chat-item DOM elements found in the left sidebar.
    Returns ConversationSummary with id, title, and URL info.
    """
    js = f"""
    (limit) => {{
        const items = document.querySelectorAll('.{CONV_ITEM_CLASS}');
        const results = [];
        for (let i = 0; i < Math.min(items.length, limit); i++) {{
            const item = items[i];
            const titleEl = item.querySelector('[class*="title"], [class*="Title"]');
            const title = titleEl ? titleEl.textContent.trim() : item.textContent.trim();
            const href = item.getAttribute('href') || '';
            const id = href.split('/chat/')[1] || '';
            const isActive = item.className.includes('{CONV_ACTIVE_CLASS}');
            results.push({{
                id: id,
                title: title.substring(0, 60),
                is_active: isActive,
            }});
        }}
        return results;
    }}
    """
    try:
        raw = page.evaluate(js, limit)
        return [
            ConversationSummary(
                id=r["id"],
                title=r["title"],
                preview="(active)" if r.get("is_active") else "",
            )
            for r in raw if r["id"]
        ]
    except Exception:
        return []


def open_conversation(page: Page, conv_id: str) -> bool:
    """Navigate to a specific conversation by ID.

    Returns True if navigation succeeded.
    """
    try:
        page.goto(f"https://www.doubao.com/chat/{conv_id}", timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(1.5)
        return True
    except Exception:
        return False


def delete_conversation(page: Page, conv_id: str) -> bool:
    """Delete a conversation from history.

    1. Find the conversation item in sidebar
    2. Hover to reveal menu button
    3. Click delete option
    4. Confirm deletion

    Returns True if deletion was triggered.
    """
    try:
        # Navigate to the target conversation first (not current one)
        current_url = page.url
        page.goto(f"https://www.doubao.com/chat/{conv_id}", timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(1.5)

        # Hover over the active conversation item to reveal menu
        active_item = page.locator(f".{CONV_ACTIVE_CLASS}").first
        if active_item.count() == 0:
            active_item = page.locator(f"[href*='/chat/{conv_id}']").first
        if active_item.count() > 0:
            active_item.hover()
            time.sleep(0.5)

            # Look for menu button that appears on hover
            menu_btn = page.locator(
                f"[href*='/chat/{conv_id}'] [class*='menu'], "
                f"[href*='/chat/{conv_id}'] [class*='more'], "
                f".{CONV_ACTIVE_CLASS} [class*='menu'], "
                f".{CONV_ACTIVE_CLASS} [class*='more']"
            ).first
            if menu_btn.count() > 0:
                menu_btn.click()
                time.sleep(0.5)

                # Find delete option in popup
                delete_btn = page.locator(
                    '[role="menu"] text=删除, '
                    '[data-state="open"] text=删除, '
                    'text=删除对话'
                ).first
                if delete_btn.count() > 0:
                    delete_btn.click()
                    time.sleep(0.5)
                    # Confirm if there's a confirmation dialog
                    confirm = page.locator(
                        'button:has-text("确定"), button:has-text("确认"), '
                        'button:has-text("删除")'
                    ).first
                    if confirm.count() > 0 and confirm.is_visible():
                        confirm.click()
                    time.sleep(1)
                    return True

        # Fallback: navigate back to original page, but report failure
        if current_url and current_url != page.url:
            page.goto(current_url, timeout=10000)
        return False  # delete controls not found
    except Exception:
        return False
