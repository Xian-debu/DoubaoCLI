"""Tests for doubao.message_actions."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doubaocli.message_actions import (
    copy_response, like_response, dislike_response,
    regenerate, get_multi_responses,
)


def make_page():
    page = MagicMock()
    btn = MagicMock()
    btn.count.return_value = 0
    page.locator.return_value.first = btn
    return page


def test_copy_not_found():
    page = make_page()
    ok = copy_response(page)
    assert ok is False


def test_like_not_found():
    page = make_page()
    ok = like_response(page)
    assert ok is False


def test_dislike_not_found():
    page = make_page()
    ok = dislike_response(page)
    assert ok is False


def test_regenerate_not_found():
    page = make_page()
    ok = regenerate(page)
    assert ok is False


def test_get_multi_responses_empty():
    page = make_page()
    page.evaluate.return_value = []
    results = get_multi_responses(page)
    assert results == []


def test_get_multi_responses_with_data():
    page = make_page()
    page.evaluate.return_value = ["Answer 1 text", "Answer 2 text"]
    results = get_multi_responses(page)
    assert len(results) == 2


def run_all():
    test_copy_not_found()
    test_like_not_found()
    test_dislike_not_found()
    test_regenerate_not_found()
    test_get_multi_responses_empty()
    test_get_multi_responses_with_data()
    print(f"  [message_actions] 6 tests passed")


if __name__ == "__main__":
    run_all()
