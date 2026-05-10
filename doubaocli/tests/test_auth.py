"""Tests for doubao.auth cookie parsing and validation."""

import sys
import os
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doubaocli.auth import parse_netscape_cookies, cookies_to_header
from doubaocli.config import AuthStatus


SAMPLE_NETSCAPE = """# Netscape HTTP Cookie File
# test
.doubao.com	TRUE	/	TRUE	1780000000	sessionid	abc123def456
.doubao.com	TRUE	/	TRUE	1780000000	passport_csrf_token	token789
www.doubao.com	FALSE	/chat	FALSE	-1	hook_slardar_session_id	sess001
"""


def test_parse_netscape_basic():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(SAMPLE_NETSCAPE)
        f.flush()
        path = f.name

    try:
        cookies = parse_netscape_cookies(path)
        assert len(cookies) == 3, f"Expected 3 cookies, got {len(cookies)}"

        names = {c["name"] for c in cookies}
        assert "sessionid" in names
        assert "passport_csrf_token" in names
        assert "hook_slardar_session_id" in names
    finally:
        os.unlink(path)


def test_parse_netscape_domain_filter():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(SAMPLE_NETSCAPE)
        f.flush()
        path = f.name

    try:
        cookies = parse_netscape_cookies(path, domain_filter="doubao.com")
        assert len(cookies) == 3
    finally:
        os.unlink(path)


def test_parse_netscape_filter_no_match():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(SAMPLE_NETSCAPE)
        f.flush()
        path = f.name

    try:
        cookies = parse_netscape_cookies(path, domain_filter="XYZ.com")
        assert len(cookies) == 0
    finally:
        os.unlink(path)


def test_parse_netscape_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("# just a comment\n\n")
        f.flush()
        path = f.name

    try:
        cookies = parse_netscape_cookies(path)
        assert len(cookies) == 0
    finally:
        os.unlink(path)


def test_parse_netscape_missing_file():
    cookies = parse_netscape_cookies("/nonexistent/cookies.txt")
    assert len(cookies) == 0


def test_cookies_to_header():
    cookies = [
        {"name": "a", "value": "1"},
        {"name": "b", "value": "2"},
    ]
    h = cookies_to_header(cookies)
    assert h == "a=1; b=2"


def test_cookies_to_header_empty():
    h = cookies_to_header([])
    assert h == ""


def test_auth_status_not_logged_in():
    cookies = [
        {"name": "hook_slardar_session_id", "value": "123", "domain": ".doubao.com"},
        {"name": "i18next", "value": "zh", "domain": ".doubao.com"},
    ]
    from doubaocli.config import AUTH_INDICATORS
    auth_key = None
    for c in cookies:
        if c["name"] in AUTH_INDICATORS and c["value"] and c["value"].strip():
            auth_key = c["name"]
            break
    assert auth_key is None


def test_auth_status_logged_in():
    cookies = [
        {"name": "sessionid", "value": "abc123", "domain": ".doubao.com"},
    ]
    from doubaocli.config import AUTH_INDICATORS
    auth_key = None
    for c in cookies:
        if c["name"] in AUTH_INDICATORS and c["value"] and c["value"].strip():
            auth_key = c["name"]
            break
    assert auth_key == "sessionid"


def test_auth_status_empty_value():
    cookies = [
        {"name": "sessionid", "value": "", "domain": ".doubao.com"},
    ]
    from doubaocli.config import AUTH_INDICATORS
    auth_key = None
    for c in cookies:
        if c["name"] in AUTH_INDICATORS and c["value"] and c["value"].strip():
            auth_key = c["name"]
            break
    assert auth_key is None


def test_parse_value_extraction():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(SAMPLE_NETSCAPE)
        f.flush()
        path = f.name

    try:
        cookies = parse_netscape_cookies(path)
        sess = [c for c in cookies if c["name"] == "sessionid"]
        assert len(sess) == 1
        assert sess[0]["value"] == "abc123def456"
    finally:
        os.unlink(path)


def run_all():
    test_parse_netscape_basic()
    test_parse_netscape_domain_filter()
    test_parse_netscape_filter_no_match()
    test_parse_netscape_empty_file()
    test_parse_netscape_missing_file()
    test_cookies_to_header()
    test_cookies_to_header_empty()
    test_auth_status_not_logged_in()
    test_auth_status_logged_in()
    test_auth_status_empty_value()
    test_parse_value_extraction()
    print(f"  [auth] 11 tests passed")


if __name__ == "__main__":
    run_all()
