from src.app.summary_queue.wait_state import QueueRetryWaitState


def test_wait_state_counts_down_and_clears_at_zero():
    state = QueueRetryWaitState()
    state.begin(2, "Retry in 2s")

    assert state.snapshot() == (True, 2, "Retry in 2s")
    assert state.tick() is True
    assert state.snapshot() == (True, 1, "Retry in 2s")
    assert state.tick() is False
    assert state.snapshot() == (False, 0, "")


def test_wait_state_normalizes_non_positive_delays():
    state = QueueRetryWaitState()

    state.begin(-4, "ignored")

    assert state.snapshot() == (False, 0, "ignored")
    assert state.tick() is False
    assert state.snapshot() == (False, 0, "")
