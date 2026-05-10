"""Mode and skill switching for Doubao chat.

Controls the 2 modes (快速/超能模式) and 15 skill tools
(6 visible chips + 9 in the "更多" popup menu).
"""

import time

from playwright.sync_api import Page

from .config import (
    MODE_CHIPS,
    SKILL_CHIPS_VISIBLE,
    SKILL_CHIPS_POPUP,
    SKILL_POPUP_TRIGGER,
)

ALL_SKILLS = SKILL_CHIPS_VISIBLE + SKILL_CHIPS_POPUP


def switch_mode(page: Page, mode: str) -> bool:
    """Switch between 'quick' (快速) and 'super' (超能模式).

    Returns True if mode was switched.
    """
    chip_text = MODE_CHIPS.get(mode)
    if not chip_text:
        return False

    try:
        chip = page.locator(chip_text).first
        if chip.count() > 0:
            chip.click()
            time.sleep(1.5)
            # Dismiss onboarding dialog if present
            _dismiss_onboarding(page)
            return True
    except Exception:
        pass
    return False


def get_active_mode(page: Page) -> str | None:
    """Detect currently active mode. Returns 'quick', 'super', or None."""
    try:
        # Check for 超能模式 active state
        super_chip = page.locator(MODE_CHIPS["super"]).first
        if super_chip.count() > 0:
            cls = super_chip.get_attribute("class") or ""
            parent_cls = super_chip.locator("..").first.get_attribute("class") or ""
            if "active" in cls or "selected" in cls or "active" in parent_cls:
                return "super"

        quick_chip = page.locator(MODE_CHIPS["quick"]).first
        if quick_chip.count() > 0:
            cls = quick_chip.get_attribute("class") or ""
            parent_cls = quick_chip.locator("..").first.get_attribute("class") or ""
            if "active" in cls or "selected" in cls or "active" in parent_cls:
                return "quick"

        # Default: 快速 is the default mode
        if quick_chip.count() > 0:
            return "quick"
        if super_chip.count() > 0:
            return "super"
    except Exception:
        pass
    return None


def select_skill(page: Page, skill_name: str) -> bool:
    """Select a skill tool by name. 15 skills available.

    Visible: PPT生成, 图像生成, 帮我写作
    Popup (via 更多): 视频生成, 翻译, 编程, 深入研究,
                      AI播客, 记录会议, 音乐生成, 解题答疑, 数据分析

    Returns True if skill was selected.
    """
    if skill_name not in ALL_SKILLS:
        return False

    try:
        # Check if skill is visible
        chip = page.locator(f"text={skill_name}").first
        if chip.count() > 0 and chip.is_visible():
            chip.click()
            time.sleep(1)
            return True

        # Need to open "更多" popup
        if skill_name in SKILL_CHIPS_POPUP:
            more_btn = page.locator(SKILL_POPUP_TRIGGER).first
            if more_btn.count() > 0:
                more_btn.click()
                time.sleep(0.5)
                # Find skill in popup
                popup_item = page.locator(f"[role=\"menu\"] text={skill_name}, "
                                          f"[data-state=\"open\"] text={skill_name}").first
                if popup_item.count() == 0:
                    popup_item = page.locator(f"text={skill_name}").last
                if popup_item.count() > 0:
                    popup_item.click()
                    time.sleep(1)
                    return True
    except Exception:
        pass
    return False


def get_available_skills(page: Page) -> list[str]:
    """List all currently accessible skills. Always returns the full set."""
    return list(ALL_SKILLS)


def _dismiss_onboarding(page: Page):
    """Dismiss the 超能模式 onboarding dialog if present."""
    try:
        dialog = page.locator('[role="dialog"]:has-text("超能模式")').first
        if dialog.count() > 0 and dialog.is_visible():
            close_btn = dialog.locator('button:has-text("开始使用"), button:has-text("知道了"), '
                                       'button:has-text("关闭"), [class*="close"]').first
            if close_btn.count() > 0:
                close_btn.click()
                time.sleep(0.5)
            else:
                page.keyboard.press("Escape")
                time.sleep(0.5)
    except Exception:
        pass
