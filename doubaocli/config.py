"""Configuration for DoubaoCLI — all paths are configurable, nothing hardcoded.

Priority: env var > config file > auto-detect > default.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


# ── Paths (configurable via env vars) ─────────────────────
def _get_default_config_dir() -> Path:
    return Path(os.environ.get("DOUBAO_CONFIG_DIR", Path.home() / ".doubaocli"))

CDP_URL = os.environ.get("DOUBAO_CDP_URL", "http://localhost:9222")
CONFIG_DIR = _get_default_config_dir()
DEFAULT_COOKIE_PATH = Path(os.environ.get(
    "DOUBAO_COOKIE_PATH",
    CONFIG_DIR / "cookies.txt"
)).expanduser()


# ── Browser Detection ─────────────────────────────────────
def detect_browser_cdp() -> str | None:
    """Try to find a running browser with CDP on common ports."""
    import urllib.request
    ports = [9222, 9223, 9229]
    for port in ports:
        try:
            url = f"http://localhost:{port}/json/version"
            urllib.request.urlopen(url, timeout=2)
            return url.replace("/json/version", "")
        except Exception:
            continue
    return None


# ── Auth Cookie Indicators (common to ByteDance SSO) ─────
AUTH_INDICATORS = [
    "sessionid", "sessionid_ss", "passport_csrf_token",
    "passport_csrf_token_default", "sid_tt", "uid_tt", "uid_tt_ss",
    "sid_guard", "sid_ucp_v1", "ssid_ucp_v1",
]


# ── UI Selectors (public DOM knowledge, version-independent where possible) ─
TEXTAREA_SELECTORS = [
    'textarea[placeholder*="发消息"]',
    'textarea[placeholder*="消息"]',
    '[contenteditable="true"]',
    '.semi-input-textarea',
]

NEW_CHAT_SELECTORS = [
    'text=新对话',
    'button:has-text("新对话")',
    '[class*="new-chat"]',
]

FILE_INPUT_SELECTOR = 'input[type="file"]'

MODE_CHIPS = {"quick": 'text=快速', "super": 'text=超能模式'}

SKILL_CHIPS_VISIBLE = ["PPT 生成", "图像生成", "帮我写作"]
SKILL_CHIPS_POPUP = [
    "视频生成", "翻译", "编程", "深入研究",
    "AI 播客", "记录会议", "音乐生成", "解题答疑", "数据分析",
]

MESSAGE_ACTION_BAR = '[class*="message-action-bar"]'

CONV_ITEM_CLASS = "chat-item-r3aVVV"

IMAGE_CREATE_URL = "https://www.doubao.com/chat/create-image"

# ── Dataclasses ────────────────────────────────────────────

@dataclass
class ChatResult:
    text: str | None = None
    conversation_id: str | None = None
    elapsed: float = 0.0
    error: str | None = None


@dataclass
class AuthStatus:
    is_logged_in: bool
    auth_key: str | None = None
    cookie_count: int = 0
    session_valid: bool | None = None


@dataclass
class ConversationSummary:
    id: str
    title: str = ""
    preview: str = ""


@dataclass
class ImageResult:
    urls: list[str] = field(default_factory=list)
    prompt: str = ""
    model: str = ""
    elapsed: float = 0.0
    error: str | None = None


@dataclass
class PageInfo:
    index: int
    title: str
    url: str
    conversation_id: str | None = None


# ── Errors ─────────────────────────────────────────────────

class DoubaoError(Exception): pass
class ConnectionError(DoubaoError): pass
class AuthError(DoubaoError): pass
class PageNotFoundError(DoubaoError): pass
class RateLimitError(DoubaoError): pass
class TimeoutError(DoubaoError): pass
