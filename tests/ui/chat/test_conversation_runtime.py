from src.ui.chat.conversation_runtime import ChatConversationRuntime


class _Signal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, value):
        for callback in list(self._callbacks):
            callback(value)


class _FakeThread:
    def __init__(self, *_args):
        self.finished = _Signal()
        self.error = _Signal()
        self.running = False
        self.started = False
        self.interruption_requested = False
        self.quit_called = False
        self.waited_for = None
        self.deleted = False

    def isRunning(self):
        return self.running

    def start(self):
        self.started = True
        self.running = True

    def requestInterruption(self):
        self.interruption_requested = True

    def quit(self):
        self.quit_called = True

    def wait(self, timeout):
        self.waited_for = timeout
        self.running = False

    def deleteLater(self):
        self.deleted = True


def _runtime(thread_factory=lambda *args: _FakeThread(), valid=True):
    return ChatConversationRuntime(
        thread_factory=thread_factory,
        provider_validator=lambda _settings: (valid, "Missing provider token"),
        settings_factory=lambda *_args: object(),
    )


def test_invalid_provider_does_not_create_or_start_a_worker():
    runtime = _runtime(valid=False)

    result = runtime.start("Question", "Context", [], lambda _: None, lambda _: None)

    assert result.started is False
    assert result.validation_error == "Missing provider token"
    assert runtime.thread is None


def test_runtime_wires_callbacks_and_releases_completed_worker():
    thread = _FakeThread()
    runtime = _runtime(thread_factory=lambda *args: thread)
    received = []
    started = []

    result = runtime.start(
        "Question",
        "Context",
        [{"role": "user", "content": "Question"}],
        received.append,
        lambda error: received.append(f"error:{error}"),
        lambda: started.append(True),
    )
    thread.finished.emit("Answer")

    assert result.started is True
    assert started == [True]
    assert received == ["Answer"]
    assert runtime.thread is None
    assert thread.deleted is True


def test_runtime_reports_worker_errors_and_releases_the_failed_worker():
    thread = _FakeThread()
    runtime = _runtime(thread_factory=lambda *args: thread)
    errors = []

    runtime.start("Question", "Context", [], lambda _: None, errors.append)
    thread.error.emit("Provider unavailable")

    assert errors == ["Provider unavailable"]
    assert runtime.thread is None
    assert thread.deleted is True


def test_runtime_prevents_parallel_workers_and_cleans_up_active_worker():
    first_thread = _FakeThread()
    runtime = _runtime(thread_factory=lambda *args: first_thread)
    runtime.start("Question", "Context", [], lambda _: None, lambda _: None)

    second = runtime.start("Another", "Context", [], lambda _: None, lambda _: None)
    runtime.cleanup()

    assert second.started is False
    assert first_thread.interruption_requested is True
    assert first_thread.quit_called is True
    assert first_thread.waited_for == 3000
    assert first_thread.deleted is True
    assert runtime.thread is None
