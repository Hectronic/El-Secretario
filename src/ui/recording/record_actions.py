"""User actions for an open recording detail widget."""

import logging
import os

from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QMessageBox

from src.ui.recording.state import fallback_record_title


class RecordingActionsCoordinator:
    """Own recording detail actions while the widget retains Qt signals and UI state."""

    def __init__(self, widget):
        self.widget = widget

    def delete_recording(self):
        record_id = self.widget.current_record_id
        if not record_id:
            return
        if QMessageBox.question(self.widget, "Delete", "Are you sure?") != QMessageBox.StandardButton.Yes:
            return

        filename = self.widget.db.delete(record_id)
        if filename:
            self._delete_audio_file(filename)
        if self.widget.rag:
            try:
                self.widget.rag.delete_document(str(record_id))
            except Exception:
                logging.exception("Failed removing record_id=%s from RAG", record_id)
        self.widget.recording_deleted.emit(record_id)

    @staticmethod
    def _delete_audio_file(filename):
        try:
            file_path = os.path.join(os.getcwd(), "recordings", filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            logging.exception("Failed deleting recording file %s", filename)

    def open_audio_editor(self):
        record_id = self.widget.current_record_id
        if record_id is not None:
            self.widget.open_audio_editor_requested.emit(int(record_id))

    def open_chat_for_recording(self):
        record_id = self.widget.current_record_id
        if not record_id:
            return
        record = self.widget.db.fetch_record(record_id)
        if not isinstance(record, dict):
            return
        title = fallback_record_title(record_id, record.get("title"))
        self.widget.start_chat_requested.emit(
            [{"type": "recording", "value": int(record_id), "label": title}]
        )

    def play_audio(self):
        self.widget.player.play()

    def pause_audio(self):
        self.widget.player.pause()

    def stop_audio(self):
        self.widget.player.stop()

    def position_changed(self, position):
        self.widget.slider.setValue(position)

    def duration_changed(self, duration):
        self.widget.slider.setRange(0, duration)

    def set_position(self, position):
        self.widget.player.setPosition(position)

    def media_state_changed(self, _state):
        if self.widget.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            self.stop_audio()

    def enable_playback_controls(self):
        self._set_playback_controls_enabled(True)

    def disable_playback_controls(self):
        self._set_playback_controls_enabled(False)

    def _set_playback_controls_enabled(self, enabled):
        for attribute in (
            "play_btn",
            "pause_btn",
            "stop_btn",
            "ask_meeting_btn",
            "retranscribe_btn",
            "delete_btn",
            "edit_audio_btn",
        ):
            control = getattr(self.widget, attribute, None)
            if control is not None:
                control.setEnabled(enabled)
