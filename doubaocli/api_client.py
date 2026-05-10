"""HTTP API client for Doubao chat completion.

WARNING: The REST API at /samantha/chat/completion is behind ByteDance's
shark_admin anti-bot system. Rapid requests WILL be rate-limited
(error code 710022002). For reliable use, prefer ChatSession (browser UI).

This client is a fallback for low-frequency, single-turn queries.
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

from .config import DEFAULT_COOKIE_PATH, ChatResult, RateLimitError, TimeoutError
from .pacing import HumanPacer
from .auth import AuthManager, cookies_to_header


class DoubaoAPIClient:
    """HTTP API client for Doubao chat.

    Auth: Cookie-based (Netscape-format cookie file).
    Transport: SSE (Server-Sent Events) over HTTP POST.
    """

    API_URL = "https://www.doubao.com/samantha/chat/completion"
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    def __init__(self, cookie_path: str | Path = DEFAULT_COOKIE_PATH,
                 pacer: HumanPacer | None = None):
        self.cookie_path = Path(cookie_path)
        self.pacer = pacer

    def chat(self, prompt: str, max_wait: int = 90) -> ChatResult:
        """Send a chat message via HTTP API.

        Returns ChatResult with text from SSE response.
        Sets error field for rate limits, auth failures, timeouts.
        """
        t0 = time.time()

        # Rate limit check
        if self.pacer:
            ok, msg = self.pacer.check_limit()
            if not ok:
                return ChatResult(error=f"Rate limited: {msg}", elapsed=time.time() - t0)
            cool = self.pacer.cooldown()
            if cool > 0:
                time.sleep(cool)

        # Load cookies
        cookies = AuthManager().load(self.cookie_path)
        if not cookies:
            return ChatResult(
                error="No cookies found. Run 'cookies extract' first.",
                elapsed=time.time() - t0,
            )

        # Build request
        content = json.dumps({"text": prompt})
        body = json.dumps({
            "messages": [{"role": "user", "content": content}],
        })

        headers = {
            "User-Agent": self.UA,
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cookie": cookies_to_header(cookies),
            "Origin": "https://www.doubao.com",
            "Referer": "https://www.doubao.com/chat",
        }

        try:
            req = urllib.request.Request(self.API_URL, data=body.encode(), headers=headers)
            with urllib.request.urlopen(req, timeout=max_wait) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return ChatResult(
                error=f"HTTP {e.code}",
                elapsed=time.time() - t0,
            )
        except Exception as e:
            return ChatResult(
                error=f"Request failed: {e}",
                elapsed=time.time() - t0,
            )

        # Parse SSE
        events = self._parse_sse(raw)
        text = self._extract_text(events)
        error = self._extract_error(events)

        # Record action
        if self.pacer:
            self.pacer.record("api_query")

        return ChatResult(
            text=text,
            error=error,
            elapsed=time.time() - t0,
            raw_text=raw[:2000],
        )

    def _parse_sse(self, raw: str) -> list[dict]:
        """Parse Server-Sent Events response."""
        events = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if not data_str:
                continue
            try:
                event = json.loads(data_str)
                if "event_data" in event and isinstance(event["event_data"], str):
                    try:
                        event["event_data"] = json.loads(event["event_data"])
                    except json.JSONDecodeError:
                        pass
                events.append(event)
            except json.JSONDecodeError:
                continue
        return events

    def _extract_text(self, events: list[dict]) -> str | None:
        """Extract response text from SSE events.

        Known event types:
        - 2003: stream end (empty event_data)
        - 2005: error/block (event_data contains error info)
        - Others: content chunks
        """
        text_parts = []
        for evt in events:
            etype = evt.get("event_type")
            if etype in (2003, 2005):
                continue
            edata = evt.get("event_data")
            if isinstance(edata, dict):
                for field in ("text", "content", "delta", "message", "answer"):
                    if field in edata and edata[field]:
                        text_parts.append(str(edata[field]))
            elif isinstance(edata, str) and edata:
                text_parts.append(edata)
        return "".join(text_parts) if text_parts else None

    def _extract_error(self, events: list[dict]) -> str | None:
        """Extract error info from SSE events."""
        for evt in events:
            etype = evt.get("event_type")
            if etype == 2005:
                edata = evt.get("event_data")
                if isinstance(edata, dict):
                    msg = edata.get("message", "")
                    detail = edata.get("error_detail", {})
                    detail_msg = detail.get("message", "") if isinstance(detail, dict) else ""
                    return detail_msg or msg or str(edata)
                return str(edata)
        return None
