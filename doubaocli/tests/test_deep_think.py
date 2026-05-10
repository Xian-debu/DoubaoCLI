"""Tests for doubao.deep_think."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doubaocli.deep_think import (
    enable, disable, is_enabled,
    get_thinking_process, get_search_sources,
)


def make_page():
    return MagicMock()


def test_enable_chip_not_found():
    page = make_page()
    chip = MagicMock()
    chip.count.return_value = 0
    page.locator.return_value.first = chip
    ok = enable(page)
    assert ok is False


def test_disable_chip_not_found():
    page = make_page()
    chip = MagicMock()
    chip.count.return_value = 0
    page.locator.return_value.first = chip
    ok = disable(page)
    assert ok is False


def test_is_enabled_not_found():
    page = make_page()
    chip = MagicMock()
    chip.count.return_value = 0
    page.locator.return_value.first = chip
    result = is_enabled(page)
    assert result is False


def test_get_thinking_empty():
    page = make_page()
    page.evaluate.return_value = None
    result = get_thinking_process(page)
    assert result is None


def test_get_thinking_with_content():
    page = make_page()
    page.evaluate.return_value = "思考过程：让我们一步步分析..."
    result = get_thinking_process(page)
    assert "思考" in result


def test_get_search_sources_empty():
    page = make_page()
    page.evaluate.return_value = []
    result = get_search_sources(page)
    assert result == []


def test_get_search_sources_with_data():
    page = make_page()
    page.evaluate.return_value = [
        {"title": "Source 1", "url": "https://example.com/1"},
        {"title": "Source 2", "url": "https://example.com/2"},
    ]
    result = get_search_sources(page)
    assert len(result) == 2
    assert result[0]["title"] == "Source 1"


def run_all():
    test_enable_chip_not_found()
    test_disable_chip_not_found()
    test_is_enabled_not_found()
    test_get_thinking_empty()
    test_get_thinking_with_content()
    test_get_search_sources_empty()
    test_get_search_sources_with_data()
    print(f"  [deep_think] 7 tests passed")


if __name__ == "__main__":
    run_all()
