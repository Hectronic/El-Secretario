import sys
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication, QWidget

from src.ui.main_window import tab_lifecycle as tab_lifecycle_module
from src.ui.main_window.tab_lifecycle import TabLifecycleCoordinator


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication(sys.argv)
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


class _Tabs:
    def __init__(self):
        self.widgets = []

    def widget(self, index):
        if index < 0 or index >= len(self.widgets):
            return None
        return self.widgets[index]

    def addTab(self, widget, _title):
        self.widgets.append(widget)
        return len(self.widgets) - 1

    def removeTab(self, index):
        self.widgets.pop(index)

    def count(self):
        return len(self.widgets)


class _Widget(QWidget):
    def __init__(self):
        super().__init__()
        self.cleanup_calls = 0
        self.delete_calls = 0

    def cleanup(self):
        self.cleanup_calls += 1

    def deleteLater(self):
        self.delete_calls += 1


class _WelcomeWidget(_Widget):
    pass


class _RecordingWidget(_Widget):
    def __init__(self, has_unsaved_changes=False, save_ok=True):
        super().__init__()
        self._has_unsaved_changes = has_unsaved_changes
        self._save_ok = save_ok

    def has_unsaved_changes(self):
        return self._has_unsaved_changes

    def save_all_changes(self):
        return self._save_ok


class _RecordingInProgressWidget(_Widget):
    def __init__(self, recording_started=False):
        super().__init__()
        self.recording_started = recording_started
        self.finish_calls = 0

    def finish_recording(self):
        self.finish_calls += 1


class _Window:
    def __init__(self):
        self.central_tabs = _Tabs()
        self.show_welcome_screen = MagicMock()
        self._sync_chat_context_section = MagicMock()


def _coordinator(monkeypatch):
    monkeypatch.setattr(tab_lifecycle_module, "WelcomeWidget", _WelcomeWidget)
    monkeypatch.setattr(tab_lifecycle_module, "RecordingWidget", _RecordingWidget)
    monkeypatch.setattr(tab_lifecycle_module, "RecordingInProgressWidget", _RecordingInProgressWidget)
    return TabLifecycleCoordinator(_Window())


def test_close_tab_ignores_welcome_widget(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    welcome = _WelcomeWidget()
    coordinator.window.central_tabs.addTab(welcome, "Welcome")

    coordinator.close_tab(0)
    assert coordinator.window.central_tabs.count() == 1
    assert welcome.delete_calls == 0


def test_close_tab_recording_in_progress_defers_removal(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    recording = _RecordingInProgressWidget(recording_started=True)
    coordinator.window.central_tabs.addTab(recording, "Rec")

    coordinator.close_tab(0)
    assert recording.finish_calls == 1
    assert coordinator.window.central_tabs.count() == 1


def test_close_tab_removes_widget_and_syncs(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    one = _Widget()
    two = _Widget()
    coordinator.window.central_tabs.addTab(one, "1")
    coordinator.window.central_tabs.addTab(two, "2")

    coordinator.close_tab(0)
    assert coordinator.window.central_tabs.count() == 1
    assert one.cleanup_calls == 1
    assert one.delete_calls == 1
    coordinator.window._sync_chat_context_section.assert_called_once()


def test_close_other_tabs_keeps_target(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    keep = _Widget()
    coordinator.window.central_tabs.addTab(_Widget(), "1")
    coordinator.window.central_tabs.addTab(keep, "2")
    coordinator.window.central_tabs.addTab(_Widget(), "3")

    coordinator.close_other_tabs(1)
    assert coordinator.window.central_tabs.count() == 1
    assert coordinator.window.central_tabs.widget(0) is keep


def test_close_all_tabs_shows_welcome_when_empty(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    coordinator.window.central_tabs.addTab(_Widget(), "1")
    coordinator.window.central_tabs.addTab(_Widget(), "2")

    coordinator.close_all_tabs()
    assert coordinator.window.central_tabs.count() == 0
    assert coordinator.window.show_welcome_screen.call_count >= 1
