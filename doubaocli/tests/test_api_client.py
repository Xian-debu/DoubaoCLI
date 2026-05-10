"""Tests for doubao.api_client SSE parsing and HTTP client."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doubaocli.api_client import DoubaoAPIClient

# Real SSE sample from Doubao API
SAMPLE_SSE = """event: gateway-error
data: {"code":"Internal","message":"error"}

data: {"event_data":"{\\"text\\":\\"hello world\\"}","event_id":"0","event_type":1}
data: {"event_data":"{\\"text\\":\\" from doubao\\"}","event_id":"1","event_type":1}
data: {"event_data":"{}","event_id":"2","event_type":2003}

"""

SAMPLE_SSE_ERROR = """data: {"event_data":"{\\"code\\":710022002,\\"message\\":\\"block\\",\\"error_detail\\":{\\"code\\":710022002,\\"locale\\":\\"zh\\",\\"message\\":\\"当前服务访问频繁\\"}}","event_id":"0","event_type":2005}
data: {"event_data":"{}","event_id":"1","event_type":2003}
"""


def test_parse_sse_valid():
    client = DoubaoAPIClient()
    events = client._parse_sse(SAMPLE_SSE)
    assert len(events) >= 3
    # First non-gateway event should have event_type=1
    evt = events[1]  # skip gateway-error line
    assert evt.get("event_type") == 1


def test_parse_sse_text_extraction():
    client = DoubaoAPIClient()
    events = client._parse_sse(SAMPLE_SSE)
    text = client._extract_text(events)
    assert text is not None
    assert "hello world" in text
    assert "from doubao" in text


def test_parse_sse_skips_empty():
    client = DoubaoAPIClient()
    events = client._parse_sse("data: \n\ndata: {}\n")
    assert len(events) == 1


def test_parse_sse_skips_non_data():
    client = DoubaoAPIClient()
    events = client._parse_sse("event: something\ndata: {\"a\":1}\n")
    assert len(events) == 1
    assert events[0]["a"] == 1


def test_parse_sse_error():
    client = DoubaoAPIClient()
    events = client._parse_sse(SAMPLE_SSE_ERROR)
    err = client._extract_error(events)
    assert err is not None
    assert "当前服务访问频繁" in err


def test_parse_sse_no_error():
    client = DoubaoAPIClient()
    events = client._parse_sse(SAMPLE_SSE)
    err = client._extract_error(events)
    assert err is None


def test_extract_text_with_nested_event_data():
    client = DoubaoAPIClient()
    events = client._parse_sse(SAMPLE_SSE)
    # Verify event_data is auto-parsed
    evt = events[1]
    edata = evt.get("event_data")
    assert isinstance(edata, dict)
    assert edata.get("text") == "hello world"


def test_ua_header():
    client = DoubaoAPIClient()
    assert "Chrome" in client.UA
    assert "Windows" in client.UA


def run_all():
    test_parse_sse_valid()
    test_parse_sse_text_extraction()
    test_parse_sse_skips_empty()
    test_parse_sse_skips_non_data()
    test_parse_sse_error()
    test_parse_sse_no_error()
    test_extract_text_with_nested_event_data()
    test_ua_header()
    print(f"  [api_client] 8 tests passed")


if __name__ == "__main__":
    run_all()
