import time
from orchestrator import QuiescenceLatch


def test_quiescence_latch() -> None:
    latch = QuiescenceLatch(window_s=0.05)

    # Not all terminal -> False, resets start
    assert latch.check(all_terminal=False) is False
    assert latch._start is None

    # All terminal, but first check -> False, sets start
    assert latch.check(all_terminal=True) is False
    assert latch._start is not None

    # Still within window -> False
    assert latch.check(all_terminal=True) is False

    # Wait for window to expire
    time.sleep(0.06)

    # Window expired -> True
    assert latch.check(all_terminal=True) is True


def test_quiescence_latch_interrupted() -> None:
    latch = QuiescenceLatch(window_s=0.1)

    assert latch.check(all_terminal=True) is False
    time.sleep(0.05)

    # Interrupted -> False, resets start
    assert latch.check(all_terminal=False) is False
    assert latch._start is None

    # Subsequent terminal check resets clock
    assert latch.check(all_terminal=True) is False
    time.sleep(0.11)

    assert latch.check(all_terminal=True) is True


def test_quiescence_reset() -> None:
    latch = QuiescenceLatch()
    latch.check(all_terminal=True)
    assert latch._start is not None

    latch.reset()
    assert latch._start is None
