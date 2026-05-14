"""Doubao chat session orchestrator.

Sends messages via browser UI interaction and extracts responses.
Primary interaction path — reliable, no API rate limits.
"""

import time
import re

from playwright.sync_api import Page

from .config import (
    TEXTAREA_SELECTORS,
    NEW_CHAT_SELECTORS,
    CONV_ITEM_CLASS,
    ChatResult,
    ConversationSummary,
    ImageResult,
)
from .browser import CDPManager
from .auth import AuthManager
from .pacing import HumanPacer


class ChatSession:
    """Orchestrates Doubao chat via browser UI.

    Coordinates CDPManager (browser), AuthManager (login state),
    and HumanPacer (rate limits).

    Usage:
        cdp = CDPManager()
        cdp.connect()
        auth = AuthManager(cdp)
        pacer = HumanPacer()
        chat = ChatSession(cdp, auth, pacer)

        result = chat.send("Hello")
        print(result.text)
    """

    def __init__(self, cdp: CDPManager, auth: AuthManager,
                 pacer: HumanPacer | None = None):
        self.cdp = cdp
        self.auth = auth
        self.pacer = pacer or HumanPacer()
        self._current_conversation_id: str | None = None

    def send(self, prompt: str, *, new_conversation: bool = False,
             timeout: int = 120) -> ChatResult:
        """Send a message and wait for the response."""
        t0 = time.time()

        try:
            # Rate limit
            ok, msg = self.pacer.check_limit()
            if not ok:
                return ChatResult(error=msg, elapsed=time.time() - t0)

            cool = self.pacer.cooldown()
            if cool > 0:
                time.sleep(cool)

            # Get or create the right page
            page = self._resolve_page(new_conversation)
            if not page:
                return ChatResult(error="No doubao page found", elapsed=time.time() - t0)

            # Focus the page (bring tab to foreground)
            try:
                page.bring_to_front()
            except Exception:
                pass

            # Auth check
            status = self.auth.is_logged_in(browser_check=True)
            if not status.is_logged_in:
                return ChatResult(error="Not logged in", elapsed=time.time() - t0)

            # Find textarea
            textarea = None
            for sel in TEXTAREA_SELECTORS:
                try:
                    el = page.locator(sel).first
                    if el.count() > 0:
                        textarea = el
                        break
                except Exception:
                    pass

            if not textarea:
                return ChatResult(error="Cannot find textarea", elapsed=time.time() - t0)

            # Human-paced interaction
            delay = self.pacer.typing_delay(len(prompt))
            textarea.click()
            time.sleep(max(0.5, delay * 0.2))

            textarea.fill(prompt)
            time.sleep(max(0.3, delay * 0.1))

            # Capture last text before sending (virtual list prevents row-count detection)
            last_text_before = self._get_last_assistant_text(page, min_rows=1) or ""

            # Send
            textarea.press("Enter")

            # Wait for response (content-based detection, works with virtual lists)
            response = self._wait_for_response(page, timeout, last_text_before, prompt)

            # Reading delay
            if response:
                time.sleep(self.pacer.reading_delay(len(response)))

            self.pacer.record("query")

            # Update conversation ID from URL
            url = page.url
            if "/chat/" in url:
                self._current_conversation_id = url.split("/chat/")[-1]

            return ChatResult(
                text=response,
                conversation_id=self._current_conversation_id,
                elapsed=time.time() - t0,
                error=None if response else "No response received",
            )

        except Exception as e:
            return ChatResult(error=str(e), elapsed=time.time() - t0)

    def start_new(self) -> bool:
        """Start a new conversation. Returns True on success."""
        page = self.cdp.page
        if not page:
            return False

        for sel in NEW_CHAT_SELECTORS:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    el.click()
                    time.sleep(2)
                    self._current_conversation_id = None
                    # Refresh page reference (find_page sets cdp._page internally)
                    self.cdp.find_page(url_filter="doubao.com/chat")
                    return True
            except Exception:
                pass

        # Fallback: navigate to base chat URL
        try:
            page.goto("https://www.doubao.com/chat", timeout=15000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)
            self._current_conversation_id = None
            return True
        except Exception:
            return False

    def get_conversations(self, limit: int = 10) -> list[ConversationSummary]:
        """Extract conversation list from the sidebar. Best-effort."""
        page = self.cdp.page
        if not page:
            return []

        js = f"""
        (limit) => {{
            const items = document.querySelectorAll('.{CONV_ITEM_CLASS}');
            const results = [];
            for (let i = 0; i < Math.min(items.length, limit); i++) {{
                const item = items[i];
                const titleEl = item.querySelector('[class*="title"], [class*="Title"]');
                const title = titleEl ? titleEl.textContent.trim() : item.textContent.trim();
                const href = item.getAttribute('href') || '';
                const id = href.split('/chat/')[1] || '';
                results.push({{
                    id: id || String(i),
                    title: title.substring(0, 60),
                    preview: '',
                }});
            }}
            return results;
        }}
        """
        try:
            raw = page.evaluate(js, limit)
            return [
                ConversationSummary(id=r["id"], title=r["title"], preview=r["preview"])
                for r in raw
            ]
        except Exception:
            return []

    # ── Extended send methods ────────────────────────────────

    def send_with_mode(self, prompt: str, mode: str = "super",
                       timeout: int = 180) -> ChatResult:
        """Send a message in a specific mode (quick/super).

        Switches to the requested mode before sending.
        """
        from .modes import switch_mode
        page = self.cdp.page
        if not page:
            return ChatResult(error="No page available")
        switch_mode(page, mode)
        time.sleep(1)
        return self.send(prompt, timeout=timeout)

    def send_with_skill(self, prompt: str, skill: str,
                        timeout: int = 180) -> ChatResult:
        """Send a message with a specific skill tool selected.

        15 skills available: PPT生成, 图像生成, 帮我写作, 视频生成,
        翻译, 编程, 深入研究, AI播客, 记录会议, 音乐生成, 解题答疑, 数据分析
        """
        from .modes import select_skill
        page = self.cdp.page
        if not page:
            return ChatResult(error="No page available")
        select_skill(page, skill)
        time.sleep(1)
        return self.send(prompt, timeout=timeout)

    def send_multi(self, prompt: str, timeout: int = 180) -> ChatResult:
        """Send in multi-response comparison mode.

        Doubao generates 5 parallel answers labeled 回答：一 through 回答：五.
        The ChatResult.text contains all 5 answers concatenated.
        """
        from .message_actions import get_multi_responses

        # First, try to activate multi-response mode by using a prompt
        # that naturally triggers comparison
        result = self.send(prompt, new_conversation=True, timeout=timeout)
        if result.error:
            return result

        # Wait for multi responses to appear
        time.sleep(3)
        responses = get_multi_responses(self.cdp.page)
        if responses:
            result.text = "\n\n---\n\n".join(
                f"回答 {i+1}: {r}" for i, r in enumerate(responses)
            )
        return result

    def send_image(self, prompt: str, timeout: int = 120) -> ImageResult:
        """Generate an AI image via the /chat/create-image page.

        Returns ImageResult with URLs of generated images.
        """
        from .image_gen import navigate, generate, ImageResult
        page = self.cdp.page
        if not page:
            return ImageResult(error="No page available")

        if "create-image" not in page.url:
            if not navigate(page):
                return ImageResult(error="Cannot navigate to create-image page")

        return generate(page, prompt, timeout=timeout)

    def get_thinking(self) -> str | None:
        """Get deep thinking process from last response (超能模式)."""
        from .deep_think import get_thinking_process
        page = self.cdp.page
        if not page:
            return None
        return get_thinking_process(page)

    def get_sources(self) -> list[dict]:
        """Get web search sources from last response (超能模式)."""
        from .deep_think import get_search_sources
        page = self.cdp.page
        if not page:
            return []
        return get_search_sources(page)

    # ── Message actions ──────────────────────────────────────

    def like(self) -> bool:
        """Like the last assistant response."""
        from .message_actions import like_response
        page = self.cdp.page
        if not page:
            return False
        return like_response(page)

    def dislike(self) -> bool:
        """Dislike the last assistant response."""
        from .message_actions import dislike_response
        page = self.cdp.page
        if not page:
            return False
        return dislike_response(page)

    def regenerate(self, timeout: int = 120) -> bool:
        """Regenerate the last assistant response."""
        from .message_actions import regenerate
        page = self.cdp.page
        if not page:
            return False
        return regenerate(page, timeout)

    # ── File / Multimodal methods ────────────────────────────

    def send_with_file(self, prompt: str, file_path: str,
                       timeout: int = 180,
                       new_conversation: bool = False) -> ChatResult:
        """Upload a file and send a prompt.

        Args:
            new_conversation: If True, opens a new browser tab to /chat
                              which starts a fresh conversation automatically.
        """
        from .file_upload import upload_file

        if new_conversation:
            # Open a completely new tab — no conversation state = fresh conversation
            try:
                page = self.cdp.new_page(url="https://www.doubao.com/chat")
                time.sleep(3)
            except Exception as e:
                return ChatResult(error=f"Cannot open new conversation: {e}")
        else:
            try:
                page = self.cdp.ensure_page()
            except Exception as e:
                return ChatResult(error=f"Page error: {e}")

        ok = upload_file(page, file_path, wait_process=True, timeout=15)
        if not ok:
            return ChatResult(error=f"Upload failed: {file_path}")

        # Doubao needs time to read and process the file content
        time.sleep(5)
        return self.send(prompt, timeout=timeout)

    def analyze_document(self, file_path: str,
                         questions: list[str] | None = None,
                         timeout: int = 300) -> dict:
        """Upload a document and do multi-turn analysis. Returns structured dict."""
        from .kb_bridge import analyze_document

        try:
            page = self.cdp.ensure_page()
        except Exception as e:
            return {"error": str(e)}

        return analyze_document(page, self, file_path, questions, timeout)

    def describe_image(self, file_path: str, question: str | None = None,
                       timeout: int = 120) -> str:
        """Upload an image and get Doubao's description."""
        from .kb_bridge import analyze_image

        try:
            page = self.cdp.ensure_page()
        except Exception as e:
            return f"ERROR: {e}"

        return analyze_image(page, self, file_path, question, timeout)

    def pdf_to_kb(self, file_path: str, category: str = "document-analysis",
                  timeout: int = 300) -> int:
        """PDF → Doubao analysis → local KB. Returns chunk count."""
        from .kb_bridge import pdf_to_kb

        try:
            page = self.cdp.ensure_page()
        except Exception:
            return 0

        return pdf_to_kb(page, self, file_path, category, timeout)

    # ── QA-specific methods ──────────────────────────────────

    def send_qa(self, question: str, quality_threshold: int = 80,
                timeout: int = 180) -> tuple[ChatResult, int]:
        """Send a Q&A question with quality assessment.

        Returns (ChatResult, quality_score).
        quality_score < quality_threshold means the answer is likely
        an echo or too short to be useful.
        """
        result = self.send(question, timeout=timeout)

        if not result.text:
            return result, 0

        # Score based on length and content
        score = len(result.text)

        # Penalize if answer echoes the question
        from .session import QASession
        if QASession._is_echo(question, result.text):
            score = min(score, 30)  # cap echo score below threshold

        # Penalize if answer is short and ends with a question mark
        # (likely just follow-up suggestions, not a real answer)
        if score < 200 and "？" in result.text[-50:]:
            score = min(score, 50)

        return result, score

    def start_fresh_conversation(self) -> bool:
        """Start a brand new conversation (navigate to /chat).
        Returns True on success.
        """
        try:
            page = self.cdp.ensure_page()
            page.goto("https://www.doubao.com/chat", timeout=15000)
            page.wait_for_load_state("domcontentloaded")
            import time
            time.sleep(2)
            return True
        except Exception:
            return False

    def _resolve_page(self, new_conversation: bool = False) -> Page | None:
        """Find the right page. Delegates to CDPManager.resolve_page()."""
        return self.cdp.resolve_page(new_conversation)

    def _count_message_rows(self, page: Page) -> int:
        """Return count of .v_list_row elements in the message list."""
        try:
            return page.evaluate(
                "() => document.querySelectorAll('.list_items .v_list_row').length"
            )
        except Exception:
            return 0

    def _wait_for_response(self, page: Page, timeout: int = 120,
                           last_text_before: str = "",
                           sent_prompt: str = "") -> str | None:
        """Wait for a new assistant message to appear.

        Uses content-based detection (not row counting) because Doubao
        uses a virtual list capped at ~10 rows where old rows scroll out
        as new ones arrive. Row count stays constant, but textContent changes.

        After sending, polls the last row until:
        (1) the text differs from last_text_before AND sent_prompt, and
        (2) the text is stable for 2 consecutive polls.
        """
        start = time.time()
        last_text = ""
        stable_count = 0

        while time.time() - start < timeout:
            time.sleep(2)

            current = self._get_last_assistant_text(page, min_rows=1)
            if current is None:
                continue

            # Skip the user's own echo (last row = sent prompt before assistant replies)
            if current.strip() == sent_prompt.strip():
                continue

            # Skip if still showing the pre-send last message
            if last_text_before and current.strip() == last_text_before.strip():
                continue

            if current == last_text:
                stable_count += 1
                if stable_count >= 2:
                    return current
            else:
                last_text = current
                stable_count = 0

        # Final attempt: return whatever is there (if different from before)
        final = self._get_last_assistant_text(page, min_rows=1)
        if final and final.strip() != last_text_before.strip() and final.strip() != sent_prompt.strip():
            return final
        return None

    def _get_last_assistant_text(self, page: Page, min_rows: int = 2) -> str | None:
        """Extract the most recent assistant message.

        Doubao DOM: .list_items > .v_list_row
        [padding, user, assistant, user, assistant, ..., padding]

        Strips suggestion chips (.suggest-message-list-wrapper) from the
        DOM before extracting textContent. This is more robust than
        text-level regex stripping because suggestions may span multiple
        lines or be space-concatenated.
        """
        js = f"""
        () => {{
            const container = document.querySelector('.list_items');
            if (!container) return null;
            const rows = container.querySelectorAll('.v_list_row');
            if (!rows || rows.length < {min_rows}) return null;

            // Find last row with meaningful content
            let lastRow = null;
            for (let i = rows.length - 1; i >= 0; i--) {{
                const text = rows[i].textContent?.trim();
                if (text && text.length > 5) {{
                    lastRow = rows[i];
                    break;
                }}
            }}
            if (!lastRow) return null;

            // Clone and strip suggestion chips before extracting text
            const clone = lastRow.cloneNode(true);
            const suggestionWrappers = clone.querySelectorAll('[class*="suggest-message-list-wrapper"]');
            for (const el of suggestionWrappers) el.remove();
            // Also strip message action bars (like/dislike/regenerate buttons)
            const actionBars = clone.querySelectorAll('[class*="message-action-bar"]');
            for (const el of actionBars) el.remove();

            return clone.textContent?.trim() || null;
        }}
        """
        try:
            return page.evaluate(js)
        except Exception:
            return None
