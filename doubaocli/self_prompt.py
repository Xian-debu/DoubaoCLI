"""Self-prompt framework for generating smart follow-up questions.

Given what's already known and what's still unknown, helps formulate
the next question that is: precise, non-redundant, deeper than the last.
"""

from .session import QASession
from .conversation_reader import get_conversation_text
from playwright.sync_api import Page


class SelfPrompter:
    """Generates the next question based on knowledge state.

    Usage:
        prompter = SelfPrompter()
        next_q = prompter.generate(session, page, question_pool)
    """

    def generate(self, session: QASession, page,
                 question_pool: list[str]) -> dict:
        """Analyze current state and produce the next question.

        Returns:
            {"question": str, "reason": str, "should_new_conv": bool,
             "urgency": "high"|"medium"|"low"}
        """
        # 1. Read current conversation
        conv_text = get_conversation_text(page)

        # 2. Find pending questions (not yet answered)
        pending = session.get_pending_questions(question_pool)

        # 3. Check context health
        should_refresh = session.should_new_conversation()
        needs_reupload = session.needs_context_refresh()

        # 4. Pick next question
        if should_refresh:
            return {
                "question": None,
                "reason": f"Context full ({session.rounds_in_current_conv}/{session.MAX_ROUNDS_PER_CONVERSATION} rounds). Need new conversation.",
                "should_new_conv": True,
                "urgency": "high",
                "pending_questions": pending,
                "conversation_summary": session.get_knowledge_summary(),
                "conversation_text": conv_text,
                "needs_reupload": True,
            }

        # Pick from pending or signal completion
        if not pending:
            session.status = session.status.__class__.COMPLETED
            return {
                "question": None,
                "reason": "All questions covered.",
                "should_new_conv": False,
                "urgency": "low",
                "pending_questions": [],
                "conversation_summary": session.get_knowledge_summary(),
                "conversation_text": conv_text,
                "needs_reupload": False,
            }

        question = pending[0]

        # Check for duplicates
        if session.is_duplicate(question):
            # Try next one
            for alt in pending[1:]:
                if not session.is_duplicate(alt):
                    question = alt
                    break
            else:
                return {
                    "question": None,
                    "reason": "All pending questions are duplicates of asked ones.",
                    "should_new_conv": False,
                    "urgency": "low",
                    "pending_questions": [],
                    "conversation_summary": session.get_knowledge_summary(),
                    "conversation_text": conv_text,
                    "needs_reupload": False,
                }

        return {
            "question": question,
            "reason": f"Next pending question ({len(pending)} remaining).",
            "should_new_conv": False,
            "urgency": "medium",
            "pending_questions": pending[1:],
            "conversation_summary": session.get_knowledge_summary(),
            "conversation_text": conv_text,
            "needs_reupload": needs_reupload,
        }
