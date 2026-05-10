"""Tests for doubao.config dataclasses and error types."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doubaocli.config import (
    ChatResult, AuthStatus, ConversationSummary,
    DoubaoError, ConnectionError, AuthError,
    PageNotFoundError, RateLimitError, TimeoutError,
    AUTH_INDICATORS, TEXTAREA_SELECTORS,
)


def test_chat_result_defaults():
    r = ChatResult()
    assert r.text is None
    assert r.error is None
    assert r.elapsed == 0.0


def test_chat_result_with_data():
    r = ChatResult(text="hello", elapsed=1.5, conversation_id="123")
    assert r.text == "hello"
    assert r.conversation_id == "123"
    assert r.error is None


def test_chat_result_error():
    r = ChatResult(error="timeout", elapsed=2.0)
    assert r.error == "timeout"
    assert r.text is None


def test_auth_status_logged_in():
    s = AuthStatus(is_logged_in=True, auth_key="sessionid", cookie_count=26, session_valid=True)
    assert s.is_logged_in
    assert s.auth_key == "sessionid"
    assert s.cookie_count == 26
    assert s.session_valid


def test_auth_status_not_logged_in():
    s = AuthStatus(is_logged_in=False, cookie_count=5)
    assert not s.is_logged_in
    assert s.auth_key is None


def test_conversation_summary():
    c = ConversationSummary(id="0", title="test", preview="hello world")
    assert c.id == "0"
    assert c.title == "test"
    assert c.preview == "hello world"


def test_error_hierarchy():
    e = ConnectionError("msg")
    assert isinstance(e, DoubaoError)
    assert isinstance(e, Exception)

    e2 = AuthError("msg")
    assert isinstance(e2, DoubaoError)

    e3 = RateLimitError("msg")
    assert isinstance(e3, DoubaoError)

    e4 = TimeoutError("msg")
    assert isinstance(e4, DoubaoError)

    e5 = PageNotFoundError("msg")
    assert isinstance(e5, DoubaoError)


def test_error_messages():
    e = ConnectionError("test message")
    assert "test message" in str(e)


def test_auth_indicators():
    assert "sessionid" in AUTH_INDICATORS
    assert "passport_csrf_token" in AUTH_INDICATORS
    assert len(AUTH_INDICATORS) > 5


def test_textarea_selectors():
    assert len(TEXTAREA_SELECTORS) >= 2
    assert any("发消息" in s for s in TEXTAREA_SELECTORS)


def run_all():
    test_chat_result_defaults()
    test_chat_result_with_data()
    test_chat_result_error()
    test_auth_status_logged_in()
    test_auth_status_not_logged_in()
    test_conversation_summary()
    test_error_hierarchy()
    test_error_messages()
    test_auth_indicators()
    test_textarea_selectors()
    print(f"  [config] 10 tests passed")


if __name__ == "__main__":
    run_all()
