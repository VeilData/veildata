import time

import pytest

from veildata.utils import Timer


def test_timer_context_manager():
    with Timer() as t:
        time.sleep(0.01)

    assert t.elapsed >= 0.01


def test_timer_manual_start_stop():
    t = Timer()
    t.start()
    time.sleep(0.01)
    t.stop()

    assert t.elapsed >= 0.01


def test_timer_elapsed_while_running():
    t = Timer()
    t.start()
    time.sleep(0.01)
    elapsed = t.elapsed
    t.stop()

    assert elapsed >= 0.01
    assert t.elapsed >= elapsed


def test_timer_not_started_error():
    t = Timer()
    with pytest.raises(RuntimeError, match="Timer was not started"):
        t.stop()

    with pytest.raises(RuntimeError, match="Timer was not started"):
        _ = t.elapsed


def test_timer_restart():
    t = Timer()
    with t:
        time.sleep(0.01)
    first_run = t.elapsed

    with t:
        time.sleep(0.02)
    second_run = t.elapsed

    assert first_run > 0
    assert second_run > 0
    assert second_run >= 0.02
