"""Configuration — all paths configurable via env vars, no hardcoded user data.

Priority: env var > default.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


# ── Paths (configurable via env vars) ─────────────────────
CDP_URL = os.environ.get("DOUBAO_CDP_URL", "http://localhost:9222")
CDP_PORT = int(os.environ.get("DOUBAO_CDP_PORT", "9222"))
BROWSER_CMD = os.environ.get("DOUBAO_BROWSER_CMD", "")  # e.g. "msedge", "google-chrome", "/custom/path"
DEFAULT_COOKIE_PATH = Path(os.environ.get(
    "DOUBAO_COOKIE_PATH",
    Path.home() / ".doubaocli" / "cookies.txt"
)).expanduser()


# ── Auth Cookie Indicators ────────────────────────────────
AUTH_INDICATORS = [
    "sessionid", "sessionid_ss", "passport_csrf_token",
    "passport_csrf_token_default", "sid_tt", "uid_tt", "uid_tt_ss",
    "sid_guard", "sid_ucp_v1", "ssid_ucp_v1", "n_mh", "odin_tt",
]

# ── Selectors (public DOM knowledge) ──────────────────────
TEXTAREA_SELECTORS = [
    'textarea[placeholder*="发消息"]', 'textarea[placeholder*="消息"]',
    '[contenteditable="true"]', '.semi-input-textarea',
]
NEW_CHAT_SELECTORS = [
    'text=新对话', 'button:has-text("新对话")', '[class*="new-chat"]', '[class*="newChat"]',
]
RESPONSE_SELECTORS = [".semi-chat-content", '[class*="message-content"]', '[class*="reply"]', ".markdown-body"]
CONVERSATION_LIST_SELECTORS = ['[class*="conversation"]', '[class*="chat-list"]', '[class*="sidebar"] [class*="item"]']

# Mode & Skill
MODE_CHIPS = {"quick": 'text=快速', "super": 'text=超能模式'}
MODE_ACTIVE_INDICATOR = '[class*="active"],[class*="selected"],[data-state="on"]'
SKILL_CHIPS_VISIBLE = ["PPT 生成", "图像生成", "帮我写作"]
SKILL_CHIPS_POPUP = ["视频生成", "翻译", "编程", "深入研究", "AI 播客", "记录会议", "音乐生成", "解题答疑", "数据分析"]
SKILL_POPUP_TRIGGER = 'text=更多'

# Message Actions
MESSAGE_ACTION_BAR = '[class*="message-action-bar"]'
MESSAGE_ACTION_BUTTONS = {
    "copy": '[class*="copy"]', "like": '[data-key="like"], [class*="like"]',
    "dislike": '[data-key="dislike"], [class*="dislike"]',
    "regenerate": '[class*="regenerate"], [class*="redo"], [class*="refresh"]',
}

# Conversation
CONV_ITEM_CLASS = "chat-item-r3aVVV"
CONV_ACTIVE_CLASS = "active-link-CytK2D"
CONV_DELETE_SELECTOR = '[class*="delete"], text=删除'
CONV_RENAME_SELECTOR = '[class*="rename"], text=重命名'

# AI Creation
IMAGE_CREATE_URL = "https://www.doubao.com/chat/create-image"
IMAGE_INPUT_SELECTORS = ['[contenteditable="true"]', 'div[class*="editor"]']
IMAGE_MODEL_SELECTOR = 'text=Seedream'
IMAGE_RATIO_SELECTOR = 'text=比例'
IMAGE_STYLE_SELECTOR = 'text=风格'
IMAGE_RESULT_SELECTORS = ['[class*="semi-image"]', 'img[class*="generated"]', '[class*="result"] img']

# Deep Think / Web Search (built into 超能模式)
THINKING_INDICATORS = ['[class*="thinking"]', '[class*="reasoning"]', '[class*="thought"]', 'details summary']
SEARCH_SOURCE_INDICATORS = ['[class*="source"]', '[class*="reference"]', '[class*="citation"]']

# File Upload
FILE_INPUT_SELECTOR = 'input[type="file"]'
UPLOAD_INDICATORS = ['[class*="attachment"]', '[class*="upload"]', '[class*="file-preview"]', '[class*="file-card"]']


# ── Dataclasses ────────────────────────────────────────────

@dataclass
class AuthStatus:
    is_logged_in: bool
    auth_key: str | None = None
    cookie_count: int = 0
    session_valid: bool | None = None

@dataclass
class ChatResult:
    text: str | None = None
    conversation_id: str | None = None
    elapsed: float = 0.0
    error: str | None = None
    raw_text: str | None = None

@dataclass
class ConversationSummary:
    id: str
    title: str = ""
    preview: str = ""
    updated_at: str | None = None

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
