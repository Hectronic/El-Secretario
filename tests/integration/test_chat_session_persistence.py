import json
from unittest.mock import MagicMock

from src.database import DBManager
from src.ui.chat.conversation_runtime import ChatConversationRuntime
from src.ui.chat_widget import ChatWidget
from src.ui.context_manager_panel import ContextManagerPanel
from src.ui.main_window.chat_floating import FloatingChatCoordinator
from src.ui.main_window.sidebar_sync import SidebarSyncCoordinator
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QPushButton, QTabWidget, QWidget, QToolButton
from PyQt6.QtCore import QObject, pyqtSignal


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


class _SignalWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, *_args):
        super().__init__()
        self.args = _args
        self.running = False
        self.interrupted = False

    def isRunning(self):
        return self.running

    def start(self):
        self.running = True

    def requestInterruption(self):
        self.interrupted = True

    def quit(self):
        pass

    def deleteLater(self):
        pass


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
    chat.input_field.setPlainText("Draft survives moving the chat")
    window = _FloatingChatWindow()
    coordinator = FloatingChatCoordinator(window)
    qtbot.addWidget(window)
    window.central_tabs.addTab(chat, "Planning")

    chat.chat_history.append({"role": "user", "content": "Keep this session."})
    chat.on_chat_finished("Persisted before floating.")
    session_id = chat.current_session_id
    coordinator.float_chat_widget(chat)
    chat.toggle_context_panel()
    assert not chat.context_panel.isHidden()
    chat.toggle_context_panel()
    assert chat.context_panel.isHidden()
    coordinator.minimize_floating_chat(chat)
    coordinator.restore_floating_chat(chat)
    coordinator.dock_chat_widget_to_tab(chat)

    saved = next(session for session in db.fetch_chat_sessions() if session["id"] == session_id)
    assert "Persisted before floating." in saved["messages"]
    assert window.central_tabs.currentWidget() is chat
    assert chat.display_mode == "tab"
    assert chat.context_panel.isHidden()
    assert chat.input_field.toPlainText() == "Draft survives moving the chat"


def test_cancelled_request_restores_draft_and_never_persists_a_fake_turn(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "chat-cancel.sqlite"))
    worker = _SignalWorker()
    runtime = ChatConversationRuntime(
        thread_factory=lambda *_args: worker,
        provider_validator=lambda _settings: (True, ""),
        settings_factory=lambda *_args: object(),
    )
    widget = ChatWidget(
        MagicMock(search=MagicMock(return_value=[])),
        persistence=db,
        notebook_persistence=_notebook_port(),
        conversation_runtime=runtime,
    )
    qtbot.addWidget(widget)

    widget.input_field.setPlainText("Keep this editable")
    widget.send_message()
    widget.cancel_request()
    worker.running = False
    worker.finished.emit("late response must be ignored")

    assert worker.interrupted is True
    assert widget.input_field.toPlainText() == "Keep this editable"
    assert widget.chat_history == []
    assert db.fetch_chat_sessions() == []


def test_completed_answer_exposes_copy_followup_and_navigable_source(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "chat-source.sqlite"))
    worker = _SignalWorker()
    runtime = ChatConversationRuntime(
        thread_factory=lambda *_args: worker,
        provider_validator=lambda _settings: (True, ""),
        settings_factory=lambda *_args: object(),
    )
    rag = MagicMock()
    rag.search.return_value = [{
        "id": "23", "text": "The launch is planned for Friday.",
        "metadata": {"title": "Launch meeting", "type": "recording"},
        "retrieval_mode": "semantic",
    }]
    widget = ChatWidget(
        rag,
        persistence=db,
        notebook_persistence=_notebook_port(),
        conversation_runtime=runtime,
    )
    qtbot.addWidget(widget)
    opened = []
    widget.source_requested.connect(opened.append)

    widget.input_field.setPlainText("When is launch?")
    widget.send_message()
    worker.running = False
    worker.finished.emit("Friday.")

    disclosure = widget.source_list.findChildren(QToolButton)[-1]
    assert disclosure.text() == "Fuentes (1)"
    assert not disclosure.isChecked()
    disclosure.click()
    buttons = widget.source_list.findChildren(QPushButton)
    source_button = next(button for button in buttons if "Launch meeting" in button.text())
    source_button.click()

    persisted = db.fetch_chat_sessions()[0]
    assert '"source_id": "23"' in persisted["messages"]
    restored = ChatWidget(
        rag,
        session_id=persisted["id"],
        persistence=db,
        notebook_persistence=_notebook_port(),
    )
    qtbot.addWidget(restored)
    restored.source_requested.connect(opened.append)
    restored_disclosure = restored.source_list.findChildren(QToolButton)[-1]
    assert not restored_disclosure.isChecked()
    restored_disclosure.click()
    restored_source = next(
        button for button in restored.source_list.findChildren(QPushButton)
        if "Launch meeting" in button.text()
    )
    restored_source.click()

    assert opened == [23, 23]
    assert any("Copy assistant response" == button.accessibleName() for button in widget.findChildren(QPushButton))
    assert any("Ask a follow-up about this response" == button.accessibleName() for button in widget.findChildren(QPushButton))


def test_right_sidebar_context_reaches_request_and_persists_with_session(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "sidebar-chat-context.sqlite"))
    notebook_db = _notebook_port()
    record_id = db.save("brief.wav", "Sidebar selected notes", 1.0, "Sidebar context meeting")
    db.update_tags(record_id, "sidebar-tag")
    worker = _SignalWorker()

    def create_worker(*args):
        worker.args = args
        return worker

    runtime = ChatConversationRuntime(
        thread_factory=create_worker,
        provider_validator=lambda _settings: (True, ""),
        settings_factory=lambda *_args: object(),
    )
    chat = ChatWidget(
        MagicMock(), persistence=db, notebook_persistence=notebook_db,
        conversation_runtime=runtime,
    )

    class _Window:
        def __init__(self):
            self.central_tabs = QTabWidget()
            self.central_tabs.addTab(chat, "Chat")
            self._right_sidebar_last_non_chat_section = "tasks"
            self._active_right_section = None
            self.chat_context_panel = ContextManagerPanel(
                db, notebook_db, show_header=False, interactive=True
            )
            self._right_sidebar_sections = {
                "chat_context": {
                    "container": QWidget(),
                    "context_panel": self.chat_context_panel,
                },
                "tasks": {"container": QWidget()},
            }
            self.sidebar_sync = SidebarSyncCoordinator(self)
            self.sidebar_sync.bind_chat_context_panel(self.chat_context_panel)

        def _set_active_right_section(self, key):
            self._active_right_section = key

    window = _Window()
    qtbot.addWidget(chat)
    qtbot.addWidget(window.central_tabs)
    window.sidebar_sync.sync_chat_context_section(chat)
    chat.context_edit_requested.emit(chat)
    assert window._active_right_section == "chat_context"

    window.chat_context_panel.active_global_tags = ["sidebar-tag"]
    window.chat_context_panel._update_status_labels()
    window.chat_context_panel.context_changed.emit()
    assert chat.context_summary.text().find("sidebar-tag") >= 0
    assert window.chat_context_panel.remove_context_btn.isEnabled()

    chat.input_field.setPlainText("What was decided?")
    chat.send_message()
    assert "Sidebar selected notes" in worker.args[2]
    worker.running = False
    worker.finished.emit("The selected meeting covered sidebar context.")

    persisted = db.fetch_chat_sessions()[0]
    assert '"type": "tag", "value": "sidebar-tag"' in persisted["context_data"]


def test_restored_session_keeps_sources_with_each_answer(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "multiple-answer-sources.sqlite"))
    messages = [
        {"role": "user", "content": "Question one"},
        {
            "role": "assistant", "content": "Answer one",
            "sources": [{
                "source_id": "31", "title": "Source one", "role": "recording",
                "excerpt": "Excerpt one", "degraded": False,
            }],
            "retrieval_degraded": False,
        },
        {"role": "user", "content": "Question two"},
        {
            "role": "assistant", "content": "Answer two",
            "sources": [{
                "source_id": "42", "title": "Source two", "role": "note",
                "excerpt": "Excerpt two", "degraded": False,
            }],
            "retrieval_degraded": False,
        },
    ]
    session_id = db.save_chat_session(
        "Two answers", "Chat", json.dumps(messages), context_data="[]"
    )
    widget = ChatWidget(
        MagicMock(), session_id=session_id, persistence=db,
        notebook_persistence=_notebook_port(),
    )
    qtbot.addWidget(widget)
    widget.show()

    answers = [card for card in widget.display._cards if card.role == "Assistant"]
    assert len(answers) == 2
    assert [card.sources_toggle.text() for card in answers] == ["Fuentes (1)", "Fuentes (1)"]
    assert all(not card.sources_toggle.isChecked() for card in answers)
    assert not any(
        button.isVisible()
        for card in answers
        for button in card.findChildren(QPushButton)
        if button.accessibleName().startswith("Open source:")
    )

    answers[1].sources_toggle.click()

    visible_source_names = [
        button.accessibleName()
        for card in answers
        for button in card.findChildren(QPushButton)
        if button.accessibleName().startswith("Open source:") and button.isVisible()
    ]
    assert visible_source_names == ["Open source: Source two"]


def test_retry_reuses_one_user_message_and_rebuilds_current_context(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "chat-retry.sqlite"))
    old_id = db.save("old.wav", "Old context only", 1.0, "Old context")
    new_id = db.save("new.wav", "Fresh context only", 1.0, "Fresh context")
    db.update_tags(old_id, "old")
    db.update_tags(new_id, "new")
    workers = []
    runtime = ChatConversationRuntime(
        thread_factory=lambda *args: workers.append(_SignalWorker(*args)) or workers[-1],
        provider_validator=lambda _settings: (True, ""),
        settings_factory=lambda *_args: object(),
    )
    widget = ChatWidget(
        MagicMock(search=MagicMock(return_value=[])), persistence=db,
        notebook_persistence=_notebook_port(), conversation_runtime=runtime,
    )
    qtbot.addWidget(widget)
    widget.context_panel.active_global_tags = ["old"]
    widget.input_field.setPlainText("Use the current context")
    widget.send_message()
    workers[0].running = False
    workers[0].error.emit("provider internal detail")

    assert "provider internal detail" not in widget.status_label.text()
    assert len([message for message in widget.chat_history if message["role"] == "user"]) == 1
    widget.context_panel.active_global_tags = ["new"]
    widget.retry_request()
    retried = workers[1].args

    assert retried[1] == "Use the current context"
    assert "Fresh context only" in retried[2]
    assert "Old context only" not in retried[2]
    assert len([message for message in widget.chat_history if message["role"] == "user"]) == 1
    workers[1].running = False
    workers[1].finished.emit("Answer with fresh context")
    saved = db.fetch_chat_sessions()[0]
    assert saved["messages"].count("Use the current context") == 1
    assert "Answer with fresh context" in saved["messages"]


def test_edit_failed_message_restores_composer_without_duplicate_history(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "chat-edit.sqlite"))
    worker = _SignalWorker()
    runtime = ChatConversationRuntime(
        thread_factory=lambda *_args: worker,
        provider_validator=lambda _settings: (True, ""),
        settings_factory=lambda *_args: object(),
    )
    widget = ChatWidget(
        MagicMock(search=MagicMock(return_value=[])), persistence=db,
        notebook_persistence=_notebook_port(), conversation_runtime=runtime,
    )
    qtbot.addWidget(widget)
    widget.input_field.setPlainText("Edit this question")
    widget.send_message()
    worker.running = False
    worker.error.emit("failed")

    widget.edit_failed_message()

    assert widget.input_field.toPlainText() == "Edit this question"
    assert widget.chat_history == []
    assert db.fetch_chat_sessions() == []


def test_selected_context_summary_can_remove_a_specific_record(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "chat-context-summary.sqlite"))
    record_id = db.save("selected.wav", "Selected content", 1.0, "Selected record")
    widget = ChatWidget(
        MagicMock(search=MagicMock(return_value=[])),
        initial_contexts=[{"type": "recording", "value": record_id, "label": "Selected record"}],
        persistence=db,
        notebook_persistence=_notebook_port(),
    )
    qtbot.addWidget(widget)

    assert "Selected record" in widget.context_summary.text()
    widget.remove_context_item("record", record_id)

    assert widget.forced_record_ids == set()
    assert "Selected record" not in widget.context_summary.text()
