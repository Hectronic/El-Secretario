from pathlib import Path
from unittest.mock import MagicMock

from PyQt6.QtCore import QMimeData, QPointF, Qt, QUrl
from PyQt6.QtGui import QDropEvent
from PyQt6.QtWidgets import QLabel, QMainWindow

from src.ui.main_window import MainWindow
from src.ui.main_window.drag_drop import extract_supported_audio_path, is_supported_audio_path


def _mime_data(path):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    return mime


def _drop_event(path, *, action=Qt.DropAction.CopyAction):
    mime = _mime_data(path)
    event = QDropEvent(
        QPointF(10, 10), action, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    event._mime_data = mime
    return event


def test_audio_path_validation_accepts_supported_regular_files(qapp, tmp_path):
    source = tmp_path / "Interview.MP3"
    source.write_bytes(b"audio")
    assert is_supported_audio_path(str(source))
    assert extract_supported_audio_path(_mime_data(source)) == str(source)


def test_audio_path_validation_rejects_directories_unknown_extensions_and_multiple_urls(qapp, tmp_path):
    directory = tmp_path / "recording.wav"
    directory.mkdir()
    unknown = tmp_path / "notes.txt"
    unknown.write_text("not audio")
    assert not is_supported_audio_path(str(directory))
    assert extract_supported_audio_path(_mime_data(directory)) is None
    assert extract_supported_audio_path(_mime_data(unknown)) is None

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(unknown)), QUrl.fromLocalFile(str(unknown))])
    assert extract_supported_audio_path(mime) is None


def test_main_window_drag_events_show_feedback_and_route_import(qtbot, tmp_path):
    source = tmp_path / "interview.wav"
    source.write_bytes(b"audio")
    window = QMainWindow()
    qtbot.addWidget(window)
    window.drop_overlay = QLabel("Drop audio file to import", window)
    window.setup_actions = MagicMock()
    window.setup_actions.import_audio_path.return_value = 42
    window.handle_status_message = MagicMock()
    window.show()
    window.drop_overlay.hide()

    enter = _drop_event(source)
    MainWindow.dragEnterEvent(window, enter)
    assert enter.isAccepted()
    assert window.drop_overlay.isVisible()
    assert "interview.wav" in window.drop_overlay.text()

    drop = _drop_event(source)
    MainWindow.dropEvent(window, drop)
    window.setup_actions.import_audio_path.assert_called_once_with(str(source))
    window.handle_status_message.assert_called_once_with("Importing and transcribing: interview.wav")
    assert drop.isAccepted()
    assert window.drop_overlay.isHidden()


def test_main_window_rejects_unsupported_drop_and_hides_feedback(qtbot, tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("not audio")
    window = QMainWindow()
    qtbot.addWidget(window)
    window.drop_overlay = QLabel("Drop audio file to import", window)
    window.drop_overlay.show()
    window.setup_actions = MagicMock()

    event = _drop_event(source)
    MainWindow.dragEnterEvent(window, event)
    assert not event.isAccepted()
    assert window.drop_overlay.isHidden()
    assert not window.setup_actions.import_audio_path.called
