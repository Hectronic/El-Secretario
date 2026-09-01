from unittest.mock import MagicMock, patch

from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QMessageBox

from src.ui.recording.record_actions import RecordingActionsCoordinator


def _widget(record_id=7):
    widget = MagicMock()
    widget.current_record_id = record_id
    return widget


def test_delete_recording_removes_persistence_rag_and_emits_signal():
    widget = _widget()
    widget.db.delete.return_value = "recording.wav"
    coordinator = RecordingActionsCoordinator(widget)

    with patch("src.ui.recording.record_actions.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
         patch.object(coordinator, "_delete_audio_file") as delete_file:
        coordinator.delete_recording()

    widget.db.delete.assert_called_once_with(7)
    delete_file.assert_called_once_with("recording.wav")
    widget.rag.delete_document.assert_called_once_with("7")
    widget.recording_deleted.emit.assert_called_once_with(7)


def test_delete_recording_does_nothing_when_not_confirmed():
    widget = _widget()
    coordinator = RecordingActionsCoordinator(widget)

    with patch("src.ui.recording.record_actions.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
        coordinator.delete_recording()

    widget.db.delete.assert_not_called()
    widget.recording_deleted.emit.assert_not_called()


def test_open_chat_and_audio_editor_emit_existing_widget_signals():
    widget = _widget(12)
    widget.db.fetch_record.return_value = {"id": 12, "title": "Planning"}
    coordinator = RecordingActionsCoordinator(widget)

    coordinator.open_chat_for_recording()
    coordinator.open_audio_editor()

    widget.start_chat_requested.emit.assert_called_once_with(
        [{"type": "recording", "value": 12, "label": "Planning"}]
    )
    widget.open_audio_editor_requested.emit.assert_called_once_with(12)


def test_playback_actions_update_player_and_controls():
    widget = _widget()
    controls = [MagicMock() for _ in range(7)]
    (
        widget.play_btn,
        widget.pause_btn,
        widget.stop_btn,
        widget.ask_meeting_btn,
        widget.retranscribe_btn,
        widget.delete_btn,
        widget.edit_audio_btn,
    ) = controls
    coordinator = RecordingActionsCoordinator(widget)

    coordinator.play_audio()
    coordinator.pause_audio()
    coordinator.set_position(250)
    coordinator.position_changed(125)
    coordinator.duration_changed(900)
    coordinator.enable_playback_controls()

    widget.player.play.assert_called_once_with()
    widget.player.pause.assert_called_once_with()
    widget.player.setPosition.assert_called_once_with(250)
    widget.slider.setValue.assert_called_once_with(125)
    widget.slider.setRange.assert_called_once_with(0, 900)
    for control in controls:
        control.setEnabled.assert_called_with(True)


def test_end_of_media_stops_player():
    widget = _widget()
    widget.player.mediaStatus.return_value = QMediaPlayer.MediaStatus.EndOfMedia

    RecordingActionsCoordinator(widget).media_state_changed(None)

    widget.player.stop.assert_called_once_with()
