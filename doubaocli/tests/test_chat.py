"""Tests for doubao.chat ChatSession with mocked dependencies."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def make_mock_page():
    """Create a mock Playwright Page."""
    page = MagicMock()
    page.url = "https://www.doubao.com/chat"
    page.title.return_value = "豆包"

    # Mock textarea
    textarea = MagicMock()
    textarea.count.return_value = 1
    page.locator.return_value.first = textarea

    return page


def make_mock_cdp():
    from doubaocli.browser import CDPManager
    cdp = CDPManager()
    cdp._playwright = MagicMock()
    cdp._browser = MagicMock()
    cdp._browser.is_connected.return_value = True
    return cdp


def test_chat_session_init():
    from doubaocli.chat import ChatSession
    from doubaocli.browser import CDPManager
    from doubaocli.auth import AuthManager
    from doubaocli.pacing import HumanPacer

    cdp = CDPManager()
    auth = AuthManager(cdp)
    pacer = HumanPacer()
    session = ChatSession(cdp, auth, pacer)
    assert session.cdp is cdp
    assert session.auth is auth
    assert session.pacer is pacer


def test_chat_session_default_pacer():
    from doubaocli.chat import ChatSession
    from doubaocli.browser import CDPManager
    from doubaocli.auth import AuthManager

    cdp = CDPManager()
    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)
    assert session.pacer is not None


def test_start_new_no_page():
    from doubaocli.chat import ChatSession
    from doubaocli.browser import CDPManager
    from doubaocli.auth import AuthManager

    cdp = CDPManager()
    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)
    result = session.start_new()
    assert result is False


def test_get_conversations_no_page():
    from doubaocli.chat import ChatSession
    from doubaocli.browser import CDPManager
    from doubaocli.auth import AuthManager

    cdp = CDPManager()
    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)
    result = session.get_conversations()
    assert result == []


def test_send_rate_limited():
    from doubaocli.chat import ChatSession
    from doubaocli.browser import CDPManager
    from doubaocli.auth import AuthManager
    from doubaocli.pacing import HumanPacer

    cdp = make_mock_cdp()
    auth = AuthManager(cdp)
    pacer = HumanPacer()
    # Pre-fill pacer to hit limit
    for _ in range(5):
        pacer.record("query")

    session = ChatSession(cdp, auth, pacer)
    result = session.send("test")
    assert result.error is not None
    assert "Hourly" in result.error or "Limit" in result.error


def test_send_no_page():
    from doubaocli.chat import ChatSession
    from doubaocli.browser import CDPManager
    from doubaocli.auth import AuthManager

    cdp = make_mock_cdp()
    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)
    # No pages in browser
    result = session.send("test")
    assert result.error is not None


def test_get_last_assistant_text():
    from doubaocli.chat import ChatSession
    from doubaocli.browser import CDPManager
    from doubaocli.auth import AuthManager

    page = make_mock_page()
    page.evaluate.return_value = "助理的回复内容"

    cdp = CDPManager()
    cdp._page = page
    auth = AuthManager(cdp)

    session = ChatSession(cdp, auth)
    text = session._get_last_assistant_text(page)
    assert text == "助理的回复内容"


def test_chat_result_structure():
    from doubaocli.chat import ChatSession, ChatResult
    from doubaocli.browser import CDPManager
    from doubaocli.auth import AuthManager

    cdp = make_mock_cdp()
    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)

    # Verify ChatResult import works
    r = ChatResult(text="test", elapsed=1.0)
    assert r.text == "test"
    assert r.error is None


def run_all():
    test_chat_session_init()
    test_chat_session_default_pacer()
    test_start_new_no_page()
    test_get_conversations_no_page()
    test_send_rate_limited()
    test_send_no_page()
    test_get_last_assistant_text()
    test_chat_result_structure()
    print(f"  [chat] 8 tests passed")


if __name__ == "__main__":
    run_all()
