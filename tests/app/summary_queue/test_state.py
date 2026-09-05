from src.app.summary_queue.state import QueueExecutionState


def test_state_deduplicates_running_and_pending_tasks():
    state = QueueExecutionState()
    task = {"type": "recording_summary", "record_id": 7}
    state.pending.append(task)

    assert state.duplicate_state(task) == "queued"
    assert state.take_next() == task
    assert state.duplicate_state(task) == "running"


def test_state_moves_removes_and_counts_pending_tasks():
    state = QueueExecutionState()
    state.pending.extend(({"type": "a"}, {"type": "b"}))

    assert state.move_pending(1, 0) is True
    assert [task["type"] for task in state.pending] == ["b", "a"]
    assert state.remove_pending_at(1) is True
    assert state.remove_pending_at(3) is False
    assert state.pending_count == 1


def test_state_finish_and_cancel_reset_active_work():
    state = QueueExecutionState()
    task, worker = {"type": "a"}, object()
    state.pending.append(task)
    assert state.take_next() == task
    state.current_worker = worker
    state.current_task_had_error = True

    assert state.finish_current() == (task, worker)
    assert state.current_task is None
    assert state.current_worker is None
    assert state.current_task_had_error is False

    state.pending.extend(({"type": "a"}, {"type": "b"}))
    state.current_task = {"type": "running"}
    assert state.cancel_all() == (2, {"type": "running"})
    assert state.pending_count == 0
