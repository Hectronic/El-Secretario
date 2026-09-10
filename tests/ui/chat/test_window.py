from types import SimpleNamespace
from unittest.mock import MagicMock

from src.ui.chat.window import ChatWindow
from src.ui.chat_window import ChatWindow as LegacyChatWindow


class _Runtime:
    def __init__(self, response="Answer from the runtime."):
        self.response = response
        self.thread = None
        self.calls = []
        self.cleaned_up = False

    def start(self, query, context, history, on_finished, on_error, on_started=None):
        self.calls.append((query, context, list(history)))
        if on_started:
            on_started()
        on_finished(self.response)
        return SimpleNamespace(started=True, validation_error=None)

    def cleanup(self):
        self.cleaned_up = True


def _persistence():
    persistence = MagicMock()
    persistence.get_all_tags.return_value = ["planning"]
    persistence.save_chat_session.return_value = 7
    return persistence


def test_legacy_import_remains_a_compatible_chat_window_facade():
    assert LegacyChatWindow is ChatWindow


def test_chat_window_uses_injected_dependencies_and_persists_completed_response(qtbot):
    persistence = _persistence()
    rag = MagicMock(search=MagicMock(return_value=[{"text": "Ship the tests"}]))
    runtime = _Runtime()
    window = ChatWindow(rag, persistence=persistence, runtime=runtime)
    qtbot.addWidget(window)
    updated = []
    window.session_updated.connect(lambda: updated.append(True))

    window.collection_combo.setCurrentText("planning")
    window.input_field.setText("What should we ship?")
    window.send_message()

    assert runtime.calls == [
        (
            "What should we ship?",
            "Note: Ship the tests",
            [{"role": "user", "content": "What should we ship?"}],
        )
    ]
    assert window.chat_history == [
        {"role": "user", "content": "What should we ship?"},
        {"role": "assistant", "content": "Answer from the runtime."},
    ]
    persistence.save_chat_session.assert_called_once()
    assert window.current_session_id == 7
    assert updated == [True]
    assert window.send_btn.isEnabled()


def test_chat_window_shows_search_failure_without_starting_runtime(qtbot):
    persistence = _persistence()
    rag = MagicMock(search=MagicMock(side_effect=RuntimeError("index unavailable")))
    runtime = _Runtime()
    window = ChatWindow(rag, persistence=persistence, runtime=runtime)
    qtbot.addWidget(window)

    window.input_field.setText("Find my note")
    window.send_message()

    assert runtime.calls == []
    assert "Error searching notes: index unavailable" in window.display.toPlainText()
    persistence.save_chat_session.assert_not_called()


def test_chat_window_cleans_up_runtime_when_closed(qtbot):
    runtime = _Runtime()
    window = ChatWindow(MagicMock(), persistence=_persistence(), runtime=runtime)
    qtbot.addWidget(window)

    window.close()

    assert runtime.cleaned_up is True
