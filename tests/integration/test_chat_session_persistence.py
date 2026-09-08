from unittest.mock import MagicMock

from src.database import DBManager
from src.ui.chat.conversation_runtime import ChatConversationRuntime
from src.ui.chat_widget import ChatWidget
from src.ui.main_window.chat_floating import FloatingChatCoordinator
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QTabWidget, QWidget


def _notebook_port():
    port = MagicMock()
    port.get_notebooks.return_value = []
    port.get_entries.return_value = []
    return port


class _FloatingChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        central = QWidget()
        central.resize(800, 600)
        self.setCentralWidget(central)
        self.central_tabs = QTabWidget(central)
        self.central_tabs.setGeometry(0, 0, 500, 400)
        self.floating_chat_bar = QFrame(central)
        self.floating_chat_bar.setVisible(False)
        self.floating_chat_layout = QHBoxLayout(self.floating_chat_bar)
        self.floating_chat_hosts = []
        self.synced_contexts = []

    def _sync_chat_context_section(self, chat_widget=None):
        self.synced_contexts.append(chat_widget)

    def load_chat_sessions(self):
        pass

    def close_tab(self, index):
        self.central_tabs.removeTab(index)


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
        self.deleted = False

    def isRunning(self):
        return self._running

    def start(self):
        self._running = True
        self.finished.emit("Response from the deterministic provider.")
        self._running = False

    def requestInterruption(self):
        pass

    def quit(self):
        pass

    def wait(self, _timeout):
        return True

    def deleteLater(self):
        self.deleted = True


def test_chat_response_persists_and_restores_session_with_real_sqlite(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "chat.sqlite"))
    notebook_db = _notebook_port()
    rag = MagicMock()
    rag.search.return_value = []
    widget = ChatWidget(
        rag,
        initial_contexts=[{"type": "tag", "value": "planning", "label": "planning"}],
        persistence=db,
        notebook_persistence=notebook_db,
    )
    qtbot.addWidget(widget)

    widget.chat_history.append({"role": "user", "content": "What is next?"})
    widget.on_chat_finished("Ship the integration tests.")

    session_id = widget.current_session_id
    session = next(item for item in db.fetch_chat_sessions() if item["id"] == session_id)
    assert "Ship the integration tests." in session["messages"]

    restored = ChatWidget(
        rag,
        session_id=session_id,
        persistence=db,
        notebook_persistence=notebook_db,
    )
    qtbot.addWidget(restored)

    assert restored.chat_history == widget.chat_history
    assert restored.context_panel.active_global_tags == ["planning"]


def test_chat_send_worker_response_persists_and_restores_with_real_sqlite(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "chat-worker.sqlite"))
    runtime = ChatConversationRuntime(
        thread_factory=_ImmediateResponseThread,
        provider_validator=lambda _settings: (True, ""),
        settings_factory=lambda *_args: object(),
    )
    widget = ChatWidget(
        MagicMock(search=MagicMock(return_value=[])),
        initial_contexts=[{"type": "tag", "value": "planning", "label": "planning"}],
        persistence=db,
        notebook_persistence=_notebook_port(),
        conversation_runtime=runtime,
    )
    qtbot.addWidget(widget)

    widget.input_field.setText("What should we ship?")
    widget.send_message()

    session = db.fetch_chat_sessions()[0]
    restored = ChatWidget(
        MagicMock(search=MagicMock(return_value=[])),
        session_id=session["id"],
        persistence=db,
        notebook_persistence=_notebook_port(),
    )
    qtbot.addWidget(restored)

    assert [message["role"] for message in restored.chat_history] == ["user", "assistant"]
    assert restored.chat_history[-1]["content"] == "Response from the deterministic provider."
    assert restored.context_panel.active_global_tags == ["planning"]
    assert widget.send_btn.isEnabled()
    assert runtime.thread is None


def test_floating_chat_round_trip_keeps_real_persisted_session(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "floating-chat.sqlite"))
    rag = MagicMock()
    rag.search.return_value = []
    chat = ChatWidget(
        rag,
        initial_contexts=[{"type": "tag", "value": "planning", "label": "planning"}],
        persistence=db,
        notebook_persistence=_notebook_port(),
    )
    window = _FloatingChatWindow()
    coordinator = FloatingChatCoordinator(window)
    qtbot.addWidget(window)
    window.central_tabs.addTab(chat, "Planning")

    chat.chat_history.append({"role": "user", "content": "Keep this session."})
    chat.on_chat_finished("Persisted before floating.")
    session_id = chat.current_session_id
    coordinator.float_chat_widget(chat)
    coordinator.minimize_floating_chat(chat)
    coordinator.restore_floating_chat(chat)
    coordinator.dock_chat_widget_to_tab(chat)

    saved = next(session for session in db.fetch_chat_sessions() if session["id"] == session_id)
    assert "Persisted before floating." in saved["messages"]
    assert window.central_tabs.currentWidget() is chat
    assert chat.display_mode == "tab"
    assert not chat.context_panel.isHidden()
