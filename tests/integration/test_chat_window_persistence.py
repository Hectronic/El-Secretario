from src.database import DBManager
from src.ui.chat.conversation_runtime import ChatConversationRuntime
from src.ui.chat.window import ChatWindow


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, value):
        for callback in list(self.callbacks):
            callback(value)


class _ImmediateResponseThread:
    def __init__(self, *_args):
        self.finished = _Signal()
        self.error = _Signal()
        self._running = False

    def isRunning(self):
        return self._running

    def start(self):
        self._running = True
        self.finished.emit("Persisted standalone response.")
        self._running = False

    def requestInterruption(self):
        pass

    def quit(self):
        pass

    def wait(self, _timeout):
        return True

    def deleteLater(self):
        pass


class _Rag:
    def __init__(self):
        self.calls = []

    def search(self, query, n_results, tag_filter):
        self.calls.append((query, n_results, tag_filter))
        return [{"text": "A real persisted note"}]


def test_standalone_chat_window_persists_and_restores_a_real_sqlite_session(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "standalone-chat.sqlite"))
    db.update_tags(db.save_note("Note", "content"), "planning")
    rag = _Rag()
    runtime = ChatConversationRuntime(
        thread_factory=_ImmediateResponseThread,
        provider_validator=lambda _settings: (True, ""),
        settings_factory=lambda *_args: object(),
    )
    window = ChatWindow(rag, persistence=db, runtime=runtime)
    qtbot.addWidget(window)
    updates = []
    window.session_updated.connect(lambda: updates.append(True))

    window.collection_combo.setCurrentText("planning")
    window.input_field.setText("What did I plan?")
    window.send_message()

    session_id = window.current_session_id
    persisted = next(item for item in db.fetch_chat_sessions() if item["id"] == session_id)
    restored = ChatWindow(_Rag(), session_id=session_id, persistence=db)
    qtbot.addWidget(restored)

    assert rag.calls == [("What did I plan?", 5, "planning")]
    assert "Persisted standalone response." in persisted["messages"]
    assert restored.collection_combo.currentText() == "planning"
    assert restored.chat_history == window.chat_history
    assert updates == [True]
    assert window.send_btn.isEnabled()
    assert runtime.thread is None
