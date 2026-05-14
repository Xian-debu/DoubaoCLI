"""DoubaoCLI — Browser-automation CLI for ByteDance's Doubao AI assistant."""

__version__ = "1.1.0"

from .browser import CDPManager
from .auth import AuthManager
from .chat import ChatSession
from .pacing import HumanPacer
from .config import ChatResult, AuthStatus, ConversationSummary, ImageResult
from .launcher import ensure_cdp, is_cdp_available, launch_browser, find_browser

