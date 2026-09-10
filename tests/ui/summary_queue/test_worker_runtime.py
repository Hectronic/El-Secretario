from unittest.mock import MagicMock

from src.ui.summary_queue import worker_runtime


class _State:
    def __init__(self, pending, current_worker=None):
        self.pending = list(pending)
        self.current_worker = current_worker

    def take_next(self):
        return self.pending.pop(0) if self.pending else None


def test_worker_runtime_starts_one_task_and_wires_lifecycle(monkeypatch):
    state = _State([{"type": "summary", "record_id": 3}])
    worker = MagicMock()
    created = []
    lifecycle = []
    current = []

    monkeypatch.setattr(
        worker_runtime,
        "build_queue_worker",
        lambda task, **kwargs: created.append((task, kwargs)) or worker,
    )
    monkeypatch.setattr(worker_runtime, "connect_queue_worker_signals", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        worker_runtime,
        "start_queue_worker_lifecycle",
        lambda **kwargs: lifecycle.append(kwargs),
    )

    started = worker_runtime.start_next_worker_if_idle(
        state=state,
        parent="queue-parent",
        db="sqlite-port",
        rag_engine="rag-port",
        clear_wait_state=lambda: None,
        on_worker_completed=lambda *_args: None,
        on_generator_recording_summary_completed=lambda *_args: None,
        on_generator_progress=lambda *_args: None,
        emit_progress=lambda *_args: None,
        on_status_update=lambda *_args: None,
        on_error=lambda *_args: None,
        on_finished=lambda: None,
        on_retry_wait=lambda *_args: None,
        set_current_worker=current.append,
        emit_task_started=lambda *_args: None,
        append_history=lambda *_args: None,
        emit_queue_state=lambda: None,
    )

    assert started is True
    assert created[0][0] == {"type": "summary", "record_id": 3}
    assert created[0][1]["db"] == "sqlite-port"
    assert lifecycle[0]["worker"] is worker
    assert lifecycle[0]["pending_remaining"] == 0


def test_worker_runtime_keeps_idle_queue_idle_and_reports_construction_failures(monkeypatch):
    empty = _State([])
    queue_states = []

    assert worker_runtime.start_next_worker_if_idle(
        state=empty,
        parent=None,
        db=None,
        rag_engine=None,
        clear_wait_state=lambda: None,
        on_worker_completed=lambda *_args: None,
        on_generator_recording_summary_completed=lambda *_args: None,
        on_generator_progress=lambda *_args: None,
        emit_progress=lambda *_args: None,
        on_status_update=lambda *_args: None,
        on_error=lambda *_args: None,
        on_finished=lambda: None,
        on_retry_wait=lambda *_args: None,
        set_current_worker=lambda *_args: None,
        emit_task_started=lambda *_args: None,
        append_history=lambda *_args: None,
        emit_queue_state=lambda: queue_states.append("idle"),
    ) is False
    assert queue_states == ["idle"]

    errors = []
    monkeypatch.setattr(worker_runtime, "build_queue_worker", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    assert worker_runtime.start_next_worker_if_idle(
        state=_State([{"type": "summary"}]),
        parent=None,
        db=None,
        rag_engine=None,
        clear_wait_state=lambda: None,
        on_worker_completed=lambda *_args: None,
        on_generator_recording_summary_completed=lambda *_args: None,
        on_generator_progress=lambda *_args: None,
        emit_progress=lambda *_args: None,
        on_status_update=lambda *_args: None,
        on_error=errors.append,
        on_finished=lambda: None,
        on_retry_wait=lambda *_args: None,
        set_current_worker=lambda *_args: None,
        emit_task_started=lambda *_args: None,
        append_history=lambda *_args: None,
        emit_queue_state=lambda: None,
    ) is False
    assert errors == ["boom"]
