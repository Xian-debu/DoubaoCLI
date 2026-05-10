"""Tests for doubao.modes."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doubaocli.modes import (
    switch_mode, get_active_mode, select_skill,
    get_available_skills, ALL_SKILLS,
)


def make_page():
    page = MagicMock()
    chip = MagicMock()
    chip.count.return_value = 0
    chip.is_visible.return_value = False
    page.locator.return_value.first = chip
    return page


def test_all_skills_list():
    skills = get_available_skills(None)
    assert len(skills) == 12  # 3 visible + 9 popup
    assert "PPT 生成" in skills
    assert "编程" in skills
    assert "数据分析" in skills


def test_switch_mode_invalid():
    page = make_page()
    ok = switch_mode(page, "invalid")
    assert ok is False


def test_switch_mode_chip_not_found():
    page = make_page()
    ok = switch_mode(page, "quick")
    assert ok is False  # Chip count = 0


def test_select_skill_invalid():
    page = make_page()
    ok = select_skill(page, "不存在的技能")
    assert ok is False


def test_select_skill_not_found():
    page = make_page()
    ok = select_skill(page, "编程")  # popup skill, more btn not found
    assert ok is False


def test_get_active_mode_default():
    page = make_page()
    mode = get_active_mode(page)
    assert mode is None


def test_skill_categories():
    visible = ["PPT 生成", "图像生成", "帮我写作"]
    popup = ["视频生成", "翻译", "编程", "深入研究",
             "AI 播客", "记录会议", "音乐生成", "解题答疑", "数据分析"]
    assert len(visible) == 3
    assert len(popup) == 9
    assert len(ALL_SKILLS) == 12


def run_all():
    test_all_skills_list()
    test_switch_mode_invalid()
    test_switch_mode_chip_not_found()
    test_select_skill_invalid()
    test_select_skill_not_found()
    test_get_active_mode_default()
    test_skill_categories()
    print(f"  [modes] 7 tests passed")


if __name__ == "__main__":
    run_all()
