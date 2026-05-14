from src.app.summary_queue.worker_factory import build_queue_worker


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class _DailyWorker:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.recording_summary_completed = _Signal()
        self.all_tasks_finished = _Signal()
        self.progress = _Signal()


class _TranscriptionWorker:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.finished = _Signal()
        self.progress = _Signal()
        self.status_update = _Signal()


class _RagWorker:
    def __init__(self, *_args, **kwargs):
        self.kwargs = kwargs
        self.task_completed = _Signal()
        self.progress = _Signal()


class _AIWorker:
    def __init__(self, *_args, **_kwargs):
        self.task_completed = _Signal()


class _Settings:
    def __init__(self, *_args):
        pass

    def value(self, key, default=None, type=None):
        values = {
            "hf_token": "",
            "force_cpu": False,
            "compute_type": "auto",
            "transcription_backend": "auto",
        }
        return values.get(key, default)


def test_build_worker_daily_summary_connects_callbacks():
    done = []
    progress = []
    worker = build_queue_worker(
        {"type": "daily_summary", "date": "2026-05-13"},
        parent=object(),
        db=None,
        rag_engine=None,
        on_worker_completed=lambda *args: done.append("done"),
        on_generator_recording_summary_completed=lambda *args: done.append("record"),
        on_generator_progress=lambda *args: progress.append("progress"),
        on_progress_emit=lambda _v: None,
        on_status_update=lambda _m: None,
        summary_generator_cls=_DailyWorker,
    )

    assert isinstance(worker, _DailyWorker)
    assert len(worker.recording_summary_completed.callbacks) == 1
    assert len(worker.all_tasks_finished.callbacks) == 1
    assert len(worker.progress.callbacks) == 1


def test_build_worker_transcription_uses_settings_and_connects_signals():
    worker = build_queue_worker(
        {"type": "transcription", "audio_path": "/tmp/a.wav", "model_size": "base", "language": "es", "diarization": False},
        parent=object(),
        db=None,
        rag_engine=None,
        on_worker_completed=lambda *_args: None,
        on_generator_recording_summary_completed=lambda *_args: None,
        on_generator_progress=lambda *_args: None,
        on_progress_emit=lambda _v: None,
        on_status_update=lambda _m: None,
        settings_cls=_Settings,
        transcriber_cls=_TranscriptionWorker,
    )

    assert isinstance(worker, _TranscriptionWorker)
    assert len(worker.finished.callbacks) == 1
    assert len(worker.progress.callbacks) == 1
    assert len(worker.status_update.callbacks) == 1


def test_build_worker_rag_and_ai_paths():
    rag_worker = build_queue_worker(
        {"type": "rag_reindex", "reindex_scope": "missing"},
        parent=object(),
        db=object(),
        rag_engine=object(),
        on_worker_completed=lambda *_args: None,
        on_generator_recording_summary_completed=lambda *_args: None,
        on_generator_progress=lambda *_args: None,
        on_progress_emit=lambda _v: None,
        on_status_update=lambda _m: None,
        rag_reindex_thread_cls=_RagWorker,
    )
    assert isinstance(rag_worker, _RagWorker)
    assert len(rag_worker.task_completed.callbacks) == 1
    assert len(rag_worker.progress.callbacks) == 1

    progress_events = []
    ai_worker = build_queue_worker(
        {"type": "summary", "text": "x"},
        parent=object(),
        db=None,
        rag_engine=None,
        on_worker_completed=lambda *_args: None,
        on_generator_recording_summary_completed=lambda *_args: None,
        on_generator_progress=lambda *_args: None,
        on_progress_emit=lambda v: progress_events.append(v),
        on_status_update=lambda _m: None,
        ai_assistant_cls=_AIWorker,
    )
    assert isinstance(ai_worker, _AIWorker)
    assert progress_events == [-1]
    assert len(ai_worker.task_completed.callbacks) == 1
