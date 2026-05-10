"""Tests for doubao.conversation."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doubaocli.conversation import list_conversations


def make_page():
    page = MagicMock()
    return page


def test_list_conversations_empty():
    page = make_page()
    page.evaluate.return_value = []
    convs = list_conversations(page)
    assert convs == []


def test_list_conversations_with_data():
    page = make_page()
    page.evaluate.return_value = [
        {"id": "123456789012345678", "title": "Test Chat", "is_active": True},
        {"id": "876543210987654321", "title": "Another", "is_active": False},
    ]
    convs = list_conversations(page)
    assert len(convs) == 2
    assert convs[0].title == "Test Chat"
    assert convs[0].id == "123456789012345678"


def test_list_conversations_empty_id_filtered():
    page = make_page()
    page.evaluate.return_value = [
        {"id": "", "title": "No ID", "is_active": False},
        {"id": "123456789012345678", "title": "Has ID", "is_active": True},
    ]
    convs = list_conversations(page)
    assert len(convs) == 1
    assert convs[0].id == "123456789012345678"


def test_list_conversations_evaluate_fails():
    page = make_page()
    page.evaluate.side_effect = Exception("DOM error")
    convs = list_conversations(page)
    assert convs == []


def run_all():
    test_list_conversations_empty()
    test_list_conversations_with_data()
    test_list_conversations_empty_id_filtered()
    test_list_conversations_evaluate_fails()
    print(f"  [conversation] 4 tests passed")


if __name__ == "__main__":
    run_all()
