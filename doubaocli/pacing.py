"""Human-like interaction pacing for Doubao browser automation.

Simplified from llm_orchestrator.py HumanPacer — single-service focus.
"""

import random
import time


class HumanPacer:
    """Enforces human-like interaction cadence.

    Two modes:
    - casual (default): max 5 queries/hour, 2-10 min between queries
    - research: max 15 queries/burst, 3s between queries, 1h cooldown after burst

    Simulates: typing speed (~250 CPM), reading delay, query cooldown.
    """

    CASUAL_LIMIT = 5
    RESEARCH_LIMIT = 15

    def __init__(self, mode: str = "casual"):
        self._actions: list[float] = []
        self._last_action_time = 0.0
        self._mode = mode  # "casual" or "research"

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str):
        if value in ("casual", "research"):
            self._mode = value

    def reset(self):
        """Clear all recorded actions. Use for testing or session reset."""
        self._actions.clear()

    def typing_delay(self, text_length: int) -> float:
        """Return simulated typing delay in seconds (~250 CPM)."""
        if text_length <= 0:
            return 1.0
        base = (text_length / 250.0) * 60.0
        variance = base * random.uniform(-0.2, 0.3)
        return max(1.0, min(90.0, base + variance))

    def reading_delay(self, response_length: int = 0) -> float:
        """Return simulated reading delay in seconds."""
        if self._mode == "research":
            # Faster reading in research mode
            if response_length <= 0:
                return random.uniform(1, 3)
            elif response_length < 500:
                return random.uniform(2, 5)
            else:
                return random.uniform(4, 10)
        # Casual mode
        if response_length <= 0:
            return random.uniform(3, 8)
        elif response_length < 300:
            return random.uniform(3, 10)
        elif response_length < 1000:
            return random.uniform(8, 18)
        else:
            return random.uniform(12, 30)

    def cooldown(self) -> float:
        """Return required cooldown delay before next action."""
        now = time.time()
        if not self._actions:
            return 0.0
        elapsed = now - max(self._actions)
        if self._mode == "research":
            # 3 seconds between queries in research mode
            if elapsed < 3:
                return 3 - elapsed
            return 0.0
        # Casual: 2-10 min between queries
        if elapsed < 120:
            return 120 - elapsed
        return 0.0

    def check_limit(self) -> tuple[bool, str]:
        """Check if within usage limits. Returns (ok, message)."""
        self._purge()
        count = len(self._actions)
        limit = self.RESEARCH_LIMIT if self._mode == "research" else self.CASUAL_LIMIT
        if count >= limit:
            return False, f"Limit reached ({count}/{limit}). Wait for cooldown."
        return True, "ok"

    def record(self, action: str = "query"):
        """Record an action."""
        self._actions.append(time.time())
        self._last_action_time = time.time()

    def _purge(self):
        """Remove actions older than 1 hour."""
        cutoff = time.time() - 3600
        self._actions = [t for t in self._actions if t > cutoff]
