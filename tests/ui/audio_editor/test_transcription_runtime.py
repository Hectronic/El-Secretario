from src.ui.audio_editor.transcription_runtime import AudioEditorTranscriptionRuntime


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, value):
        for callback in list(self.callbacks):
            callback(value)


class _Thread:
    def __init__(self, *_args, **_kwargs):
        self.finished = _Signal()
        self.error = _Signal()
        self.running = False
        self.started = False
        self.deleted = False

    def isRunning(self):
        return self.running

    def start(self):
        self.started = True
        self.running = True

    def requestInterruption(self):
        self.running = False

    def quit(self):
        pass

    def wait(self, _timeout):
        return True

    def deleteLater(self):
        self.deleted = True


class _Settings:
    def value(self, key, default=None, **_kwargs):
        return {
            "rec_config/language": "Spanish",
            "compute_type": "auto",
            "hf_token": "token",
            "rec_config/diarization": True,
            "force_cpu": False,
            "transcription_backend": "faster-whisper",
        }.get(key, default)


def _runtime(thread_factory=_Thread, preflight_error=None):
    return AudioEditorTranscriptionRuntime(
        thread_factory=thread_factory,
        settings_factory=lambda *_args: _Settings(),
        model_resolver=lambda _settings: "large-v3",
        preflight_checker=lambda *_args: preflight_error,
    )


def test_runtime_uses_configured_options_and_releases_finished_worker():
    thread = _Thread()
    runtime = _runtime(thread_factory=lambda *_args, **_kwargs: thread)
    results = []

    start = runtime.start("edited.wav", 12.5, results.append, lambda _: None)
    thread.finished.emit({"text": "Done"})

    assert start.started is True
    assert results == [{"text": "Done"}]
    assert runtime.thread is None
    assert thread.deleted is True


def test_runtime_blocks_invalid_preflight_without_creating_worker():
    runtime = _runtime(preflight_error="Install the selected model first.")

    start = runtime.start("edited.wav", 12.5, lambda _: None, lambda _: None)

    assert start.started is False
    assert start.preflight_error == "Install the selected model first."
    assert runtime.thread is None


def test_runtime_reports_worker_error_and_releases_worker():
    thread = _Thread()
    runtime = _runtime(thread_factory=lambda *_args, **_kwargs: thread)
    errors = []

    runtime.start("edited.wav", 12.5, lambda _: None, errors.append)
    thread.error.emit("Transcription unavailable")

    assert errors == ["Transcription unavailable"]
    assert runtime.thread is None
    assert thread.deleted is True
