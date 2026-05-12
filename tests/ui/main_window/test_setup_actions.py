# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import sys
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication, QTabWidget, QWidget

from src.ui.main_window.setup_actions import SetupActionsCoordinator
from src.ui.main_window import setup_actions as setup_actions_module


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


class _FakeSettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.rag_initialize_requested = _SignalStub()
        self.rag_reload_requested = _SignalStub()
        self.rag_reindex_requested = _SignalStub()


class _FakeRecordingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.calls = []

    def start_transcription_with_config(self, dest_path, config):
        self.calls.append((dest_path, config))


def _make_window():
    window = MagicMock()
    window.central_tabs = QTabWidget()
    window._build_rag_engine = MagicMock()
    window.summary_task_queue = MagicMock()
    window.db = MagicMock()
    window.open_recording_tab = MagicMock(return_value=_FakeRecordingWidget())
    return window


def test_open_settings_tab_reuses_existing_widget_and_wires_signals(qtbot, monkeypatch):
    _app()
    monkeypatch.setattr(setup_actions_module, "SettingsWidget", _FakeSettingsWidget)

    window = _make_window()
    qtbot.addWidget(window.central_tabs)
    coordinator = SetupActionsCoordinator(window)

    coordinator.open_settings_tab()
    assert window.central_tabs.count() == 1
    widget = window.central_tabs.widget(0)
    assert isinstance(widget, _FakeSettingsWidget)

    widget.rag_initialize_requested.emit({"enabled": True})
    widget.rag_reload_requested.emit({"enabled": False})
    widget.rag_reindex_requested.emit()

    window._build_rag_engine.assert_any_call({"enabled": True}, reason="initialize")
    window._build_rag_engine.assert_any_call({"enabled": False}, reason="reload")
    window.summary_task_queue.enqueue_rag_reindex.assert_called_once_with(source="settings")

    coordinator.open_settings_tab()
    assert window.central_tabs.count() == 1
    assert window.central_tabs.currentWidget() is widget


def test_import_audio_file_uses_unique_filename_and_starts_transcription(qtbot, tmp_path, monkeypatch):
    _app()
    monkeypatch.setattr(setup_actions_module.os, "getcwd", lambda: str(tmp_path))

    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    (recordings_dir / "import.wav").write_text("existing")

    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    source_path = incoming_dir / "import.wav"
    source_path.write_text("audio")

    window = _make_window()
    qtbot.addWidget(window.central_tabs)
    qtbot.addWidget(window.open_recording_tab.return_value)
    window.db.save.return_value = 321
    coordinator = SetupActionsCoordinator(window)

    monkeypatch.setattr(
        setup_actions_module.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(source_path), "Audio Files (*.wav)"),
    )

    coordinator.import_audio_file({"mode": "fast"})

    expected_dest = recordings_dir / "import_1.wav"
    window.db.save.assert_called_once_with("import_1.wav", "", 0.0, title="import_1.wav")
    window.open_recording_tab.assert_called_once_with(321, {"mode": "fast"})
    assert window.open_recording_tab.return_value.calls == [
        (str(expected_dest), {"mode": "fast"})
    ]
