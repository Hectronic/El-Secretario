from src.app.summary_queue.worker_signals import connect_queue_worker_signals


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class _WorkerBase:
    def __init__(self):
        self.error = _Signal()
        self.finished = _Signal()


class _WorkerWithStatusAndRetry(_WorkerBase):
    def __init__(self):
        super().__init__()
        self.status_update = _Signal()
        self.retry_wait = _Signal()


def test_connect_worker_signals_for_non_transcription():
    worker = _WorkerWithStatusAndRetry()
    connect_queue_worker_signals(
        worker,
        task_type="summary",
        on_error=lambda *_args: None,
        on_finished=lambda *_args: None,
        on_status_update=lambda *_args: None,
        on_retry_wait=lambda *_args: None,
    )

    assert len(worker.error.callbacks) == 1
    assert len(worker.finished.callbacks) == 1
    assert len(worker.status_update.callbacks) == 1
    assert len(worker.retry_wait.callbacks) == 1


def test_connect_worker_signals_skips_status_for_transcription():
    worker = _WorkerWithStatusAndRetry()
    connect_queue_worker_signals(
        worker,
        task_type="transcription",
        on_error=lambda *_args: None,
        on_finished=lambda *_args: None,
        on_status_update=lambda *_args: None,
        on_retry_wait=lambda *_args: None,
    )

    assert len(worker.error.callbacks) == 1
    assert len(worker.finished.callbacks) == 1
    assert len(worker.status_update.callbacks) == 0
    assert len(worker.retry_wait.callbacks) == 1


def test_connect_worker_signals_tolerates_missing_optional_signals():
    worker = _WorkerBase()
    connect_queue_worker_signals(
        worker,
        task_type="summary",
        on_error=lambda *_args: None,
        on_finished=lambda *_args: None,
        on_status_update=lambda *_args: None,
        on_retry_wait=lambda *_args: None,
    )

    assert len(worker.error.callbacks) == 1
    assert len(worker.finished.callbacks) == 1
