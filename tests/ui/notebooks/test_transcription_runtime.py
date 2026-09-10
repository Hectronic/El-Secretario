from src.ui.notebooks.transcription_runtime import NotebookTranscriptionRuntime


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
        self.deleted = False

    def isRunning(self):
        return self.running

    def start(self):
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
    def value(self, _key, default=None, **_kwargs):
        return default


def test_notebook_runtime_wires_and_releases_finished_worker():
    thread = _Thread()
    runtime = NotebookTranscriptionRuntime(
        thread_factory=lambda *_args, **_kwargs: thread,
        settings_factory=lambda *_args: _Settings(),
        model_resolver=lambda _settings: "base",
        preflight_checker=lambda *_args: None,
    )
    results = []

    started = runtime.start("note.wav", results.append, lambda _: None)
    thread.finished.emit({"text": "Captured"})

    assert started.started is True
    assert results == [{"text": "Captured"}]
    assert runtime.thread is None
    assert thread.deleted is True


def test_notebook_runtime_does_not_start_invalid_preflight():
    runtime = NotebookTranscriptionRuntime(
        settings_factory=lambda *_args: _Settings(),
        model_resolver=lambda _settings: "sherpa-onnx",
        preflight_checker=lambda *_args: "Model missing",
    )

    started = runtime.start("note.wav", lambda _: None, lambda _: None)

    assert started.started is False
    assert started.preflight_error == "Model missing"
