"""Deep Q&A orchestrator for Doubao document analysis.

Coordinates: ChatSession + QASession + SelfPrompter + file upload.
Handles: context refresh, dedup, quality checks, retry, progress persistence.
"""

import json
import time
from pathlib import Path

from .session import QASession, QAStatus
from .self_prompt import SelfPrompter
from .conversation_reader import (
    read_conversation, has_question_been_asked, get_row_count,
)
from .file_upload import upload_file, wait_for_processing, clear_files
from .chat import ChatSession
from .browser import CDPManager


class DeepQA:
    """Multi-turn deep Q&A session with state management.

    Usage:
        cdp = CDPManager(); cdp.connect()
        session = ChatSession(cdp, auth)
        qa = DeepQA(session)

        results = qa.run("paper.pdf", questions=[
            "总结这篇论文", "方法是什么", ...
        ], max_rounds=11)
    """

    def __init__(self, chat: ChatSession, results_path: str = "/tmp/deep_qa_results.json"):
        self.chat = chat
        self.session = QASession()
        self.prompter = SelfPrompter()
        self.results_path = Path(results_path)
        self._current_questions = []
        self._original_questions = []

    def run(self, file_path: str | Path,
            questions: list[str],
            max_rounds: int = 15,
            quality_threshold: int = 80) -> list[dict]:
        """Run a complete multi-turn Q&A session.

        Args:
            file_path: PDF/document to analyze.
            questions: Initial pool of questions.
            max_rounds: Max total rounds across all conversations.
            quality_threshold: Min characters for a valid answer.

        Returns list of result dicts with question, answer, status, quality.
        """
        path = Path(file_path).expanduser().resolve()
        self._original_questions = list(questions)
        self._current_questions = list(questions)

        if not path.exists():
            return [{"error": f"File not found: {path}"}]

        results = []

        # Ensure page is ready
        page = self.chat.cdp.ensure_page()
        if not page:
            return [{"error": "No doubao page available"}]

        # Initial upload
        self._log("Uploading document...")
        if not upload_file(page, str(path), wait_process=True, timeout=30):
            return [{"error": "Upload failed"}]
        wait_for_processing(page, timeout=20)
        time.sleep(5)

        round_num = 0
        while round_num < max_rounds and self._current_questions:
            round_num += 1

            # 1. Check context health
            if self.session.should_new_conversation():
                self._log(f"Context full ({self.session.rounds_in_current_conv} rounds). Starting new conversation...")
                if self.chat.start_fresh_conversation():
                    self.session.new_conversation()
                    page = self.chat.cdp.ensure_page()  # refresh after navigation
                    time.sleep(2)
                    upload_file(page, str(path), wait_process=True, timeout=30)
                    wait_for_processing(page, timeout=20)
                    time.sleep(5)
                else:
                    self._log("ERROR: Failed to start fresh conversation, aborting")
                    break

            # 2. Read conversation history
            conv_msgs = read_conversation(page)

            # 3. Generate next question
            prompt_result = self.prompter.generate(
                self.session, page, self._current_questions
            )

            if prompt_result.get("should_new_conv"):
                if self.chat.start_fresh_conversation():
                    self.session.new_conversation()
                    page = self.chat.cdp.ensure_page()  # refresh after navigation
                    time.sleep(2)
                    upload_file(page, str(path), wait_process=True, timeout=30)
                    wait_for_processing(page, timeout=20)
                    time.sleep(5)
                    # Retry generation
                    prompt_result = self.prompter.generate(
                        self.session, page, self._current_questions
                    )
                else:
                    self._log("ERROR: Failed to start fresh conversation, skipping retry")
                    prompt_result = {}

            question = prompt_result.get("question")
            if not question:
                self._log("No more questions to ask.")
                break

            # 4. Check for dedup (double-check against actual conversation)
            if has_question_been_asked(page, question):
                self._log(f"Skipping duplicate: {question[:60]}...")
                self._current_questions = [
                    q for q in self._current_questions if q != question
                ]
                continue

            # 5. Send question with quality check
            self._log(f"Round {round_num}: {question[:80]}...")
            result, quality = self.chat.send_qa(question, quality_threshold)

            # 6. Record
            rec = self.session.record(
                question=question,
                answer=result.text or "",
                quality_score=quality,
                elapsed=result.elapsed,
                error=result.error,
            )

            results.append({
                "round": round_num,
                "conv": self.session.conversation_index,
                "question": question,
                "answer": result.text,
                "quality": quality,
                "status": rec.status,
                "elapsed": result.elapsed,
                "error": result.error,
            })

            # 7. Handle quality failures
            if rec.status == "echo":
                self._log(f"  ECHO detected (quality={quality}). Will retry in new conversation.")
                # Don't retry same question immediately - put it back and move on
                self._current_questions = [
                    q for q in self._current_questions if q != question
                ]
                # Trigger new conversation for next round
                self.session.consecutive_errors += 1
                continue

            if rec.status == "error" and "rate" in (rec.answer or "").lower():
                self._log("  Rate limited. Waiting 60s...")
                time.sleep(60)
                continue

            # 8. Remove asked question from pool
            self._current_questions = [
                q for q in self._current_questions if q != question
            ]

            # 9. Progress save
            self._save_progress(results)

            # 10. Check if we need context refresh
            if self.session.needs_context_refresh():
                self._log("  Refreshing file context...")
                clear_files(page)
                time.sleep(1)
                upload_file(page, str(path), wait_process=True, timeout=30)
                wait_for_processing(page, timeout=20)
                time.sleep(3)

            time.sleep(2)

        # Final save
        self._save_progress(results)
        self._log(f"Complete: {self.session.success_count}/{round_num} quality answers.")
        return results

    def _log(self, msg: str):
        print(f"  [DeepQA] {msg}")

    def _save_progress(self, results: list[dict]):
        self.results_path.write_text(json.dumps({
            "file": str(self._original_questions[:1]) if self._original_questions else "",
            "rounds": len(results),
            "success_count": self.session.success_count,
            "conversations": self.session.conversation_index,
            "results": results,
        }, ensure_ascii=False, indent=2))
