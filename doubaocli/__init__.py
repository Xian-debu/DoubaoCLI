"""DoubaoCLI — Browser-automation CLI for ByteDance's Doubao AI assistant."""

__version__ = "1.0.0"

from .browser import CDPManager
from .auth import AuthManager
from .chat import ChatSession
from .pacing import HumanPacer
from .config import ChatResult, AuthStatus, ConversationSummary, ImageResult

