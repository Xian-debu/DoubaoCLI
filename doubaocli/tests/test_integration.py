"""Integration test for Doubao framework with real Edge CDP.

REQUIRES: Edge running with --remote-debugging-port=9222
         User logged into doubao.com in at least one tab

If CDP is not available, all tests are SKIPPED (not FAILED).
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doubaocli.browser import CDPManager, ConnectionError
from doubaocli.auth import AuthManager
from doubaocli.chat import ChatSession
from doubaocli.pacing import HumanPacer


_skip_reason = None


def setup():
    global _skip_reason
    cdp = CDPManager()
    try:
        cdp.connect()
    except ConnectionError as e:
        _skip_reason = f"Edge CDP not available: {e}"
        return None
    return cdp


def test_connection():
    if _skip_reason:
        print(f"  SKIP: {_skip_reason}")
        return
    cdp = CDPManager()
    cdp.connect()
    assert cdp.connected, "Should be connected"
    assert cdp.find_page("doubao.com") is not None, "Should find doubao page"
    cdp.close()


def test_auth_status():
    if _skip_reason:
        print(f"  SKIP: {_skip_reason}")
        return
    cdp = CDPManager()
    cdp.connect()
    auth = AuthManager(cdp)
    status = auth.is_logged_in(browser_check=True)
    assert status.is_logged_in, f"Should be logged in, got: {status}"
    assert status.cookie_count > 0
    cdp.close()


def test_cookie_extract_and_save():
    if _skip_reason:
        print(f"  SKIP: {_skip_reason}")
        return
    cdp = CDPManager()
    cdp.connect()
    auth = AuthManager(cdp)
    cookies = auth.extract()
    assert len(cookies) > 10, f"Should have >10 cookies, got {len(cookies)}"

    count = auth.save(cookies, path="/tmp/test_doubao_cookies.txt")
    assert count == len(cookies)

    # Verify round-trip
    loaded = auth.load(path="/tmp/test_doubao_cookies.txt")
    assert len(loaded) > 0
    cdp.close()


def test_send_message():
    if _skip_reason:
        print(f"  SKIP: {_skip_reason}")
        return
    cdp = CDPManager()
    cdp.connect()
    auth = AuthManager(cdp)

    result = ChatSession(cdp, auth).send("用一句话介绍你自己", new_conversation=True, timeout=120)

    assert result.error is None, f"Chat error: {result.error}"
    assert result.text is not None, "Should have response text"
    assert len(result.text) > 5, f"Response too short: {result.text}"
    assert result.elapsed > 0

    print(f"  Response: {result.text[:100]}...")
    cdp.close()


def test_multi_turn():
    if _skip_reason:
        print(f"  SKIP: {_skip_reason}")
        return
    cdp = CDPManager()
    cdp.connect()
    auth = AuthManager(cdp)
    session = ChatSession(cdp, auth)

    r1 = session.send("回答：一", new_conversation=True, timeout=120)
    assert r1.error is None, f"Turn 1 error: {r1.error}"

    r2 = session.send("回答：二", timeout=120)
    assert r2.error is None, f"Turn 2 error: {r2.error}"

    print(f"  Turn 1: {r1.text[:60]}...")
    print(f"  Turn 2: {r2.text[:60]}...")
    cdp.close()


def test_page_management():
    if _skip_reason:
        print(f"  SKIP: {_skip_reason}")
        return
    cdp = CDPManager()
    cdp.connect()

    # List pages
    pages = cdp.list_doubao_pages()
    initial = len(pages)
    assert initial >= 1, f"Should have at least 1 doubao page, got {initial}"
    print(f"  Initial: {initial} pages")

    # Create an extra page
    ctx = list(cdp._browser.contexts)[0]
    pg = ctx.new_page()
    pg.goto("https://www.doubao.com/chat", timeout=15000)
    pg.wait_for_load_state("domcontentloaded")
    time.sleep(1)

    pages = cdp.list_doubao_pages()
    assert len(pages) == initial + 1

    # Close extra pages, keep one
    closed = cdp.close_page(index=-1)
    assert closed >= 1, f"Should close >=1 page, closed {closed}"

    final = cdp.list_doubao_pages()
    assert len(final) <= 1, f"Should have <=1 pages, got {len(final)}"

    print(f"  Final: {len(final)} pages (closed {closed})")
    cdp.close()


def run_all():
    global _skip_reason
    cdp = setup()
    if cdp:
        cdp.close()

    tests = [
        ("Connection", test_connection),
        ("Auth Status", test_auth_status),
        ("Cookie Extract", test_cookie_extract_and_save),
        ("Send Message", test_send_message),
        ("Multi-turn", test_multi_turn),
        ("Page Mgmt", test_page_management),
    ]

    passed = 0
    skipped = 0
    failed = 0

    for name, func in tests:
        try:
            func()
            print(f"  [{name}] PASS")
            passed += 1
        except AssertionError as e:
            if _skip_reason:
                print(f"  [{name}] SKIP")
                skipped += 1
            else:
                print(f"  [{name}] FAIL: {e}")
                failed += 1
        except Exception as e:
            print(f"  [{name}] ERROR: {e}")
            failed += 1

    print(f"  Passed: {passed}, Skipped: {skipped}, Failed: {failed}")


if __name__ == "__main__":
    run_all()
