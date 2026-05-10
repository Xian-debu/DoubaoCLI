"""Tests for doubao.pacing HumanPacer."""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doubaocli.pacing import HumanPacer


def test_typing_delay_short():
    pacer = HumanPacer()
    d = pacer.typing_delay(10)
    assert 1.0 <= d <= 90.0, f"Expected 1-90s, got {d}"


def test_typing_delay_medium():
    pacer = HumanPacer()
    d = pacer.typing_delay(100)
    assert 1.0 <= d <= 90.0


def test_typing_delay_empty():
    pacer = HumanPacer()
    d = pacer.typing_delay(0)
    assert d == 1.0


def test_reading_delay_short():
    pacer = HumanPacer()
    d = pacer.reading_delay(100)
    assert 3.0 <= d <= 10.0, f"Expected 3-10s, got {d}"


def test_reading_delay_medium():
    pacer = HumanPacer()
    d = pacer.reading_delay(500)
    assert 8.0 <= d <= 18.0


def test_reading_delay_long():
    pacer = HumanPacer()
    d = pacer.reading_delay(2000)
    assert 12.0 <= d <= 30.0


def test_reading_delay_zero():
    pacer = HumanPacer()
    d = pacer.reading_delay(0)
    assert 3.0 <= d <= 8.0


def test_check_limit_empty():
    pacer = HumanPacer()
    ok, msg = pacer.check_limit()
    assert ok
    assert "ok" in msg


def test_check_limit_after_actions():
    pacer = HumanPacer()
    for _ in range(5):
        pacer.record("query")
    ok, msg = pacer.check_limit()
    assert not ok
    assert "Limit" in msg


def test_check_limit_below_max():
    pacer = HumanPacer()
    for _ in range(3):
        pacer.record("query")
    ok, msg = pacer.check_limit()
    assert ok


def test_cooldown_no_prior():
    pacer = HumanPacer()
    c = pacer.cooldown()
    assert c == 0.0


def test_cooldown_after_action():
    pacer = HumanPacer()
    pacer.record("query")
    c = pacer.cooldown()
    assert c >= 0.0  # Will be positive if <120s since recording


def test_purge_old_actions():
    pacer = HumanPacer()
    # Inject an old action
    pacer._actions.append(time.time() - 7200)
    pacer._purge()
    assert len(pacer._actions) == 0


def run_all():
    test_typing_delay_short()
    test_typing_delay_medium()
    test_typing_delay_empty()
    test_reading_delay_short()
    test_reading_delay_medium()
    test_reading_delay_long()
    test_reading_delay_zero()
    test_check_limit_empty()
    test_check_limit_after_actions()
    test_check_limit_below_max()
    test_cooldown_no_prior()
    test_cooldown_after_action()
    test_purge_old_actions()
    print(f"  [pacing] 13 tests passed")


if __name__ == "__main__":
    run_all()
