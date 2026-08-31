# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication, QWidget, QTabWidget

from src.ui.main_window import recording_tabs as recording_tabs_module
from src.ui.main_window.recording_tabs import RecordingTabCoordinator


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication(sys.argv)
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


class _SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in list(self.callbacks):
            callback(*args, **kwargs)


class _DummyRecordingWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.current_record_id = kwargs.get("record_id")
        self.recording_saved = _SignalStub()
        self.recording_deleted = _SignalStub()
        self.status_changed = _SignalStub()
        self.progress_changed = _SignalStub()
        self.start_chat_requested = _SignalStub()
        self.open_audio_editor_requested = _SignalStub()
        self.close_requested = _SignalStub()
        self.cleanup_calls = 0
        self.transcription_config = None

    def set_transcription_config(self, config):
        self.transcription_config = config

    def cleanup(self):
        self.cleanup_calls += 1


def _make_window():
    window = MagicMock()
    window.central_tabs = QTabWidget()
    window.rag = object()
    window.recorder = object()
    window.summary_task_queue = object()
    window.db = MagicMock()
    window.open_chat_tab = MagicMock()
    window.close_tab = MagicMock()
    window._log_user_settings_snapshot = MagicMock()
    window.load_history = MagicMock()
    window.request_sidebar_reload = MagicMock()
    window.handle_status_message = MagicMock()
    window.handle_progress = MagicMock()
    window._sync_chat_context_section = MagicMock()
    window.show_welcome_screen = MagicMock()
    return window


def test_recording_tab_title_prefers_title_filename_then_id(monkeypatch):
    _app()
    coordinator = RecordingTabCoordinator(_make_window())

    assert coordinator.recording_tab_title({"id": 7, "title": "Weekly note"}) == "Weekly note"
    assert coordinator.recording_tab_title({"id": 7, "filename": "sample.wav"}) == "sample.wav"
    assert coordinator.recording_tab_title({"id": 7}) == "Recording 7"
    assert coordinator.recording_tab_title(None) == "New Recording"


def test_open_recording_tab_reuses_existing_and_wires_editor_request(monkeypatch):
    _app()
    monkeypatch.setattr(recording_tabs_module, "RecordingWidget", _DummyRecordingWidget)
    monkeypatch.setattr(recording_tabs_module, "AudioEditorWidget", _DummyRecordingWidget)

    window = _make_window()
    window.db.fetch_record.return_value = {"id": 123, "title": "Meeting", "filename": "meeting.wav"}
    coordinator = RecordingTabCoordinator(window)

    widget = coordinator.open_recording_tab(123, config={"foo": "bar"})
    assert widget.transcription_config == {"foo": "bar"}
    assert window.central_tabs.count() == 1
    assert window.central_tabs.tabText(0) == "Meeting"

    widget.open_audio_editor_requested.emit(123)
    window.open_recording_editor_tab.assert_called_once_with(123)

    reopened = coordinator.open_recording_tab(123)
    assert reopened is widget
    assert window.central_tabs.currentWidget() is widget


def test_close_recording_tabs_removes_matching_tabs_and_falls_back_to_welcome(monkeypatch):
    _app()
    monkeypatch.setattr(recording_tabs_module, "RecordingWidget", _DummyRecordingWidget)

    window = _make_window()
    coordinator = RecordingTabCoordinator(window)

    first = _DummyRecordingWidget(record_id=1)
    second = _DummyRecordingWidget(record_id=2)
    window.central_tabs.addTab(first, "One")
    window.central_tabs.addTab(second, "Two")

    coordinator.close_recording_tabs(1)

    assert first.cleanup_calls == 1
    assert window.central_tabs.count() == 1
    assert window.show_welcome_screen.called is False
    window._sync_chat_context_section.assert_called_once()

    coordinator.close_recording_tabs(2)
    assert second.cleanup_calls == 1
    assert window.central_tabs.count() == 0
    window.show_welcome_screen.assert_called_once()


def test_open_recording_editor_tab_sets_editor_title(monkeypatch):
    _app()
    monkeypatch.setattr(recording_tabs_module, "RecordingWidget", _DummyRecordingWidget)
    monkeypatch.setattr(recording_tabs_module, "AudioEditorWidget", _DummyRecordingWidget)

    window = _make_window()
    window.db.fetch_record.return_value = {"id": 77, "title": "Sprint review", "filename": "review.wav"}
    coordinator = RecordingTabCoordinator(window)

    editor = coordinator.open_recording_editor_tab(77)

    assert isinstance(editor, QWidget)
    assert window.central_tabs.count() == 1
    assert "Sprint review - Editor" == window.central_tabs.tabText(0)


def test_handle_recording_widget_saved_refreshes_sidebar_and_tab_title(monkeypatch):
    _app()
    monkeypatch.setattr(recording_tabs_module, "RecordingWidget", _DummyRecordingWidget)
    window = _make_window()
    window.db.fetch_record.return_value = {"id": 5, "title": "Updated"}
    coordinator = RecordingTabCoordinator(window)
    widget = _DummyRecordingWidget(record_id=5)
    window.central_tabs.addTab(widget, "Old title")

    coordinator.handle_recording_widget_saved(widget)

    window.load_history.assert_called_once()
    window.request_sidebar_reload.assert_called_once_with(include_tags=True, include_history=True)
    assert window.central_tabs.tabText(0) == "Updated"
