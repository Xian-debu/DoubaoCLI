"""Q&A session state management for Doubao deep research.

Tracks every question asked, answer received, context window health,
and knowledge gaps. Prevents duplicates and detects context fatigue.

State machine:
  ACTIVE → CONTEXT_FULL → (new conversation) → ACTIVE
  ACTIVE → RATE_LIMITED → (wait) → ACTIVE
  ACTIVE → COMPLETED (all questions covered)
  ACTIVE → FAILED (consecutive errors > threshold)
"""

import time
from dataclasses import dataclass, field
from enum import Enum


class QAStatus(Enum):
    ACTIVE = "active"
    CONTEXT_FULL = "context_full"
    RATE_LIMITED = "rate_limited"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QARecord:
    question: str
    answer: str = ""
    quality_score: int = 0
    round_num: int = 0
    elapsed: float = 0.0
    status: str = ""  # ok, echo, empty, error


class QASession:
    """Tracks a multi-turn Q&A session state.

    Prevents duplicate questions, monitors context window health,
    and maintains a knowledge map of covered topics.

    Usage:
        session = QASession()
        if session.is_duplicate("what is MCSA?"):
            print("Already covered")
        if session.should_new_conversation():
            start_fresh()
        session.record("what is MCSA?", "MCSA is...", quality=200)
    """

    MAX_ROUNDS_PER_CONVERSATION = 6
    MAX_CONSECUTIVE_ERRORS = 4
    MIN_QUALITY_CHARS = 80
    ECHO_SIMILARITY_THRESHOLD = 0.5  # answer contains >50% of question → echo

    def __init__(self):
        self.records: list[QARecord] = []
        self.status = QAStatus.ACTIVE
        self.conversation_index = 1  # increments on new conversations
        self.rounds_in_current_conv = 0
        self.consecutive_errors = 0
        self._question_hashes: set[int] = set()

    def record(self, question: str, answer: str = "",
               quality_score: int = 0, elapsed: float = 0.0,
               error: str | None = None) -> QARecord:
        """Record a Q&A round. Updates state based on quality."""
        round_num = len(self.records) + 1

        # Determine status
        if error:
            status = "error"
            self.consecutive_errors += 1
            if "rate" in error.lower() or "limit" in error.lower():
                self.status = QAStatus.RATE_LIMITED
            elif self.consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                self.status = QAStatus.FAILED
        elif quality_score < self.MIN_QUALITY_CHARS:
            status = "echo" if self._is_echo(question, answer) else "short"
            self.consecutive_errors += 1
        else:
            status = "ok"
            self.consecutive_errors = 0
            self._question_hashes.add(self._hash_question(question))

        rec = QARecord(
            question=question,
            answer=answer,
            quality_score=quality_score,
            round_num=round_num,
            elapsed=elapsed,
            status=status,
        )
        self.records.append(rec)
        self.rounds_in_current_conv += 1

        if self.rounds_in_current_conv >= self.MAX_ROUNDS_PER_CONVERSATION:
            self.status = QAStatus.CONTEXT_FULL

        return rec

    def new_conversation(self):
        """Signal that a new conversation was started."""
        self.conversation_index += 1
        self.rounds_in_current_conv = 0
        self.consecutive_errors = 0
        if self.status == QAStatus.CONTEXT_FULL or self.status == QAStatus.FAILED:
            self.status = QAStatus.ACTIVE

    def is_duplicate(self, question: str) -> bool:
        """Check if a question has already been asked."""
        h = self._hash_question(question)
        if h in self._question_hashes:
            return True
        # Fuzzy check: any word overlap > 70%
        q_words = set(question.lower().split())
        for rec in self.records:
            r_words = set(rec.question.lower().split())
            if not q_words or not r_words:
                continue
            overlap = len(q_words & r_words) / len(q_words)
            if overlap > 0.7:
                return True
        return False

    def should_new_conversation(self) -> bool:
        """Check if context is exhausted and we need a fresh conversation."""
        return (
            self.status == QAStatus.CONTEXT_FULL
            or self.rounds_in_current_conv >= self.MAX_ROUNDS_PER_CONVERSATION
            or self.consecutive_errors >= 2
        )

    def needs_context_refresh(self) -> bool:
        """Check if file context needs re-upload (every 4 rounds in same conv)."""
        return self.rounds_in_current_conv > 0 and self.rounds_in_current_conv % 4 == 0

    def get_knowledge_summary(self) -> str:
        """Summarize what's been covered so far."""
        if not self.records:
            return "(no knowledge yet)"
        lines = []
        for r in self.records:
            if r.status == "ok":
                lines.append(f"Q{r.round_num}: {r.question[:60]} → "
                             f"{r.answer[:80]}...")
        return "\n".join(lines) if lines else "(no quality answers yet)"

    def get_pending_questions(self, question_pool: list[str]) -> list[str]:
        """Filter a pool to only unanswered questions."""
        return [q for q in question_pool if not self.is_duplicate(q)]

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.records if r.status == "ok")

    @property
    def total_rounds(self) -> int:
        return len(self.records)

    @staticmethod
    def _hash_question(q: str) -> int:
        """Normalize and hash for dedup."""
        # Remove punctuation, lowercase, sort words
        words = sorted(
            w.strip("？?。.，,！!：:；;（）()\"'")
            for w in q.lower().split()
            if len(w.strip("？?。.，,！!：:；;（）()\"'")) > 1
        )
        return hash(" ".join(words))

    @staticmethod
    def _is_echo(question: str, answer: str) -> bool:
        """Check if answer is just echoing the question."""
        if not answer:
            return True
        a_words = set(answer.lower().split())
        q_words = set(question.lower().split())
        if not q_words:
            return False
        overlap = len(q_words & a_words) / len(q_words)
        return overlap > QASession.ECHO_SIMILARITY_THRESHOLD
