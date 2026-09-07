from unittest.mock import Mock

from src.app.summary_queue.execution import QueueWorkerExecutionCoordinator
from src.app.summary_queue.history import QueueHistory
from src.app.summary_queue.state import QueueExecutionState
from src.app.summary_queue.wait_state import QueueRetryWaitState


class _Timer:
    def __init__(self):
        self.active = False

    def isActive(self):
        return self.active

    def start(self):
        self.active = True

    def stop(self):
        self.active = False


class _Worker:
    def __init__(self):
        self.deleted = False

    def deleteLater(self):
        self.deleted = True


def _coordinator(state=None):
    state = state or QueueExecutionState()
    events = []
    completion_actions = Mock()
    completion_actions.return_value.apply = Mock()
    timer = _Timer()
    coordinator = QueueWorkerExecutionCoordinator(
        state=state,
        history=QueueHistory(),
        wait_state=QueueRetryWaitState(),
        wait_timer=timer,
        completion_actions=completion_actions,
        handle_completion=Mock(return_value=[{"type": "status", "message": "Done"}]),
        append_history=lambda event, task, message="": events.append((event, task, message)),
        emit_progress=Mock(),
        emit_status=Mock(),
        emit_skipped=Mock(),
        emit_failed=Mock(),
        emit_finished=Mock(),
        emit_wait_state=Mock(),
        emit_queue_state=Mock(),
        start_next=Mock(),
        retain_worker=Mock(),
        is_fatal_transcription_failure=lambda message: "timed out" in message,
    )
    return coordinator, events, completion_actions, timer


def test_worker_completion_applies_completion_actions_for_current_task():
    state = QueueExecutionState()
    state.current_task = {"type": "summary", "record_id": 4}
    coordinator, _, completion_actions, _ = _coordinator(state)

    coordinator.on_worker_completed("Summary")

    coordinator.handle_completion.assert_called_once_with(state.current_task, "Summary")
    completion_actions.return_value.apply.assert_called_once_with([{"type": "status", "message": "Done"}])


def test_fatal_transcription_error_is_skipped_and_not_failed():
    state = QueueExecutionState()
    task = {"type": "transcription", "record_id": 4}
    state.current_task = task
    coordinator, events, _, _ = _coordinator(state)

    coordinator.on_worker_error("Transcription subprocess timed out.")

    assert state.current_task_had_error is True
    assert events == [("skipped", task, "Transcription subprocess timed out.")]
    coordinator.emit_skipped.assert_called_once_with(task, "Transcription subprocess timed out.")
    coordinator.emit_failed.assert_not_called()


def test_worker_finish_releases_worker_and_starts_next_task():
    state = QueueExecutionState()
    task = {"type": "summary", "record_id": 4}
    worker = _Worker()
    state.current_task = task
    state.current_worker = worker
    coordinator, events, _, _ = _coordinator(state)

    coordinator.on_worker_completely_finished()

    assert worker.deleted is True
    coordinator.retain_worker.assert_called_once_with(worker)
    coordinator.emit_finished.assert_called_once_with(task)
    coordinator.start_next.assert_called_once_with()
    assert events == [("finished", task, "")]


def test_retry_wait_emits_state_and_starts_timer():
    coordinator, _, _, timer = _coordinator()

    coordinator.on_worker_retry_wait(2.1, 0, 3, "temporary failure")

    assert timer.active is True
    assert coordinator.wait_state.snapshot() == (True, 2, "Retry 1/3 in progress")
    coordinator.emit_status.assert_called_once_with("Waiting 2s before retry (1/3). temporary failure")
