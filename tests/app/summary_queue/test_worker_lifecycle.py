from src.app.summary_queue.worker_lifecycle import start_queue_worker_lifecycle


class _Worker:
    def __init__(self):
        self.started = False

    def start(self):
        self.started = True


def test_start_queue_worker_lifecycle_orders_core_steps():
    worker = _Worker()
    task = {"type": "summary", "record_id": 1}
    calls = []
    state = {"current": None}

    start_queue_worker_lifecycle(
        worker=worker,
        task=task,
        pending_remaining=3,
        set_current_worker=lambda w: (calls.append("set_current"), state.__setitem__("current", w)),
        emit_task_started=lambda t, remaining: calls.append(("started", t["type"], remaining)),
        append_history=lambda event, payload: calls.append(("history", event, payload["type"])),
        emit_queue_state=lambda: calls.append("emit_queue"),
    )

    assert state["current"] is worker
    assert worker.started is True
    assert calls == [
        "set_current",
        ("started", "summary", 3),
        ("history", "started", "summary"),
        "emit_queue",
    ]
