"""Read Doubao conversation history from page DOM.

Extracts all messages from .list_items > .v_list_row,
detects duplicates, measures context length.
"""

from dataclasses import dataclass
from playwright.sync_api import Page


@dataclass
class Message:
    role: str       # "user" or "assistant"
    text: str
    index: int      # row index in DOM


def read_conversation(page: Page) -> list[Message]:
    """Read ALL messages from the current conversation."""
    js = """
    () => {
        const rows = document.querySelectorAll('.list_items .v_list_row');
        const msgs = [];
        for (let i = 0; i < rows.length; i++) {
            const text = rows[i].textContent?.trim();
            if (text && text.length > 3) {
                msgs.push({
                    index: i,
                    text: text,
                    isUser: i % 2 === 1,  // odd rows = user messages
                });
            }
        }
        return msgs;
    }
    """
    try:
        raw = page.evaluate(js)
        return [
            Message(role="user" if m["isUser"] else "assistant",
                    text=m["text"], index=m["index"])
            for m in raw
        ]
    except Exception:
        return []


def read_recent_messages(page: Page, n: int = 6) -> list[Message]:
    """Read last N messages (even = N/2 Q&A pairs)."""
    all_msgs = read_conversation(page)
    return all_msgs[-n:] if len(all_msgs) > n else all_msgs


def get_conversation_text(page: Page) -> str:
    """Get all conversation text concatenated (for self-prompt context)."""
    msgs = read_conversation(page)
    lines = []
    for m in msgs[-20:]:  # Last 20 messages = ~10 Q&A pairs
        role = "USER" if m.role == "user" else "DOUBAO"
        lines.append(f"[{role}] {m.text[:500]}")
    return "\n\n".join(lines)


def has_question_been_asked(page: Page, question: str) -> bool:
    """Fuzzy check if a similar question already appears in the conversation."""
    msgs = read_conversation(page)
    q_words = set(w.strip("？?。.，,") for w in question.lower().split()
                  if len(w.strip("？?。.，,")) > 1)
    if not q_words:
        return False

    for m in msgs:
        if m.role != "user":
            continue
        m_words = set(w.strip("？?。.，,") for w in m.text.lower().split()
                      if len(w.strip("？?。.，,")) > 1)
        if not m_words:
            continue
        overlap = len(q_words & m_words) / len(q_words)
        if overlap > 0.6:
            return True
    return False


def get_row_count(page: Page) -> int:
    """Get total v_list_row count (proxy for conversation length)."""
    try:
        return page.evaluate(
            "() => document.querySelectorAll('.list_items .v_list_row').length"
        )
    except Exception:
        return 0


def get_last_answer(page: Page) -> str:
    """Get the most recent assistant message text."""
    msgs = read_conversation(page)
    for m in reversed(msgs):
        if m.role == "assistant":
            return m.text
    return ""
