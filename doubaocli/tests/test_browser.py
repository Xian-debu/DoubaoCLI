"""Tests for doubao.browser CDPManager with mocked Playwright."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_cdp_manager_init():
    from doubaocli.browser import CDPManager
    cdp = CDPManager()
    assert not cdp.connected
    assert cdp.page is None
    assert cdp.cdp_url == "http://localhost:9222"


def test_cdp_manager_custom_url():
    from doubaocli.browser import CDPManager
    cdp = CDPManager(cdp_url="http://other:9999")
    assert cdp.cdp_url == "http://other:9999"


@patch("doubaocli.browser.sync_playwright")
def test_connect_success(mock_sp):
    from doubaocli.browser import CDPManager

    mock_pw = MagicMock()
    mock_pw.chromium.connect_over_cdp.return_value = MagicMock(is_connected=lambda: True)
    mock_sp.return_value.start.return_value = mock_pw

    cdp = CDPManager()
    result = cdp.connect()
    assert result is True
    assert cdp.connected


@patch("doubaocli.browser.sync_playwright")
def test_connect_failure(mock_sp):
    from doubaocli.browser import CDPManager, ConnectionError

    mock_pw = MagicMock()
    mock_pw.chromium.connect_over_cdp.side_effect = Exception("Connection refused")
    mock_sp.return_value.start.return_value = mock_pw

    cdp = CDPManager()
    try:
        cdp.connect()
        assert False, "Should have raised ConnectionError"
    except ConnectionError as e:
        assert "Connection refused" in str(e)


def test_find_page_no_browser():
    from doubaocli.browser import CDPManager
    cdp = CDPManager()
    assert cdp.find_page() is None
    assert cdp.find_page(url_filter="test") is None


@patch("doubaocli.browser.sync_playwright")
def test_close_cleanup(mock_sp):
    from doubaocli.browser import CDPManager
    cdp = CDPManager()
    cdp._playwright = MagicMock()
    cdp._browser = MagicMock()
    cdp._page = MagicMock()
    cdp.close()
    assert cdp._browser is None
    assert cdp._page is None


def test_connected_false_initially():
    from doubaocli.browser import CDPManager
    cdp = CDPManager()
    assert not cdp.connected


def test_new_cdp_session_no_page():
    from doubaocli.browser import CDPManager, ConnectionError
    cdp = CDPManager()
    try:
        cdp.new_cdp_session()
        assert False, "Should have raised ConnectionError"
    except ConnectionError:
        pass


def run_all():
    test_cdp_manager_init()
    test_cdp_manager_custom_url()
    test_connect_success()
    test_connect_failure()
    test_find_page_no_browser()
    test_close_cleanup()
    test_connected_false_initially()
    test_new_cdp_session_no_page()
    print(f"  [browser] 8 tests passed")


if __name__ == "__main__":
    run_all()
