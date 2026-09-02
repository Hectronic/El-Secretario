"""Remaining state, editing, interaction, and cleanup support for recordings."""

import logging
import os

from src.ui.recording.audio_trim import (
    mark_trim_end,
    mark_trim_start,
    playhead_seconds,
    trim_recording_audio,
    validate_trim_request,
)
from src.ui.recording.speaker_actions import apply_speaker_mapping, find_speaker_labels
from src.ui.recording.state import recording_audio_path


class RecordingWidgetSupport:
    def __init__(self, widget):
        self.widget = widget

    def connect_dirty_tracking(self):
        for name, signal_name in (
            ("title_input", "textChanged"), ("text_display", "textChanged"),
            ("notes_display", "textChanged"), ("tags_input", "textChanged"),
            ("is_diarized_check_meta", "stateChanged"), ("trim_start_spin", "valueChanged"),
            ("trim_end_spin", "valueChanged"),
        ):
            control = getattr(self.widget, name, None)
            signal = getattr(control, signal_name, None) if control else None
            if signal is not None:
                signal.connect(self.mark_dirty)

    def mark_dirty(self, *_args):
        if not self.widget._suppress_dirty_tracking:
            self.set_dirty(True)

    def set_dirty(self, is_dirty):
        self.widget._has_unsaved_changes = bool(is_dirty)
        if getattr(self.widget, "save_all_btn", None):
            self.widget.save_all_btn.setEnabled(self.widget._has_unsaved_changes)

    def has_unsaved_changes(self):
        return self.widget._has_unsaved_changes

    def set_audio_edit_enabled(self, enabled):
        if not self.widget.audio_edit_group:
            return
        for control in (
            self.widget.audio_edit_group, self.widget.trim_start_spin,
            self.widget.trim_end_spin, self.widget.mark_start_btn,
            self.widget.mark_end_btn, self.widget.trim_btn,
        ):
            control.setEnabled(enabled)

    def configure_audio_edit_bounds(self, duration_seconds):
        duration = max(0.0, float(duration_seconds or 0.0))
        self.widget._audio_edit_start = 0.0
        self.widget._audio_edit_end = duration
        if not self.widget.audio_edit_group:
            return
        self.widget.trim_start_spin.blockSignals(True)
        self.widget.trim_end_spin.blockSignals(True)
        self.widget.trim_start_spin.setRange(0.0, duration)
        self.widget.trim_end_spin.setRange(0.0, duration)
        self.widget.trim_start_spin.setValue(0.0)
        self.widget.trim_end_spin.setValue(duration)
        self.widget.trim_start_spin.blockSignals(False)
        self.widget.trim_end_spin.blockSignals(False)
        self.set_audio_edit_enabled(duration > 0.0)

    def recording_audio_path(self, record):
        return recording_audio_path(record, os.getcwd())

    def set_record_audio_source(self, record, *, qurl):
        exists = os.path.exists(self.widget.current_recording_path)
        if exists:
            self.widget.enable_playback_controls()
            self.widget.player.setSource(qurl.fromLocalFile(self.widget.current_recording_path))
        else:
            self.widget.disable_playback_controls()
            self.widget.status_changed.emit("Audio file not found.")
        return exists and record["duration"] > 0.0

    def mark_trim_start(self):
        if not self.widget.trim_start_spin:
            return
        start, end = mark_trim_start(
            self.widget.trim_start_spin.value(), self.widget.trim_end_spin.value(),
            playhead_seconds(self.widget.player.position()),
        )
        self.widget.trim_start_spin.setValue(start)
        self.widget.trim_end_spin.setValue(end)

    def mark_trim_end(self):
        if not self.widget.trim_end_spin:
            return
        start, end = mark_trim_end(
            self.widget.trim_start_spin.value(), self.widget.trim_end_spin.value(),
            playhead_seconds(self.widget.player.position()),
        )
        self.widget.trim_start_spin.setValue(start)
        self.widget.trim_end_spin.setValue(end)

    def trim_audio_selection(self, *, trim_func, qurl, message_box):
        widget = self.widget
        if not widget.audio_edit_group:
            return
        start, end = float(widget.trim_start_spin.value()), float(widget.trim_end_spin.value())
        error = validate_trim_request(widget.current_recording_path, start, end)
        if error:
            message_box.warning(widget, "Error", error)
            return
        try:
            duration = trim_recording_audio(widget.current_recording_path, start, end, trim_func)
            widget.db.update_duration(widget.current_record_id, duration)
            if getattr(widget, "duration_label", None):
                widget.duration_label.setText(f"{duration:.1f}s")
            widget._configure_audio_edit_bounds(duration)
            widget.player.setSource(qurl.fromLocalFile(widget.current_recording_path))
            widget._set_dirty(False)
            widget.recording_saved.emit()
            widget.status_changed.emit("Audio trimmed. Retranscribing...")
            widget.start_transcription(widget.current_recording_path)
        except Exception as exc:
            logging.exception("Failed to trim audio for record_id=%s", widget.current_record_id)
            message_box.critical(widget, "Trim Error", str(exc))

    def update_transcription_actions(self):
        text = self.widget.text_display.toPlainText() if self.widget.text_display else ""
        if self.widget.copy_transcription_btn:
            self.widget.copy_transcription_btn.setEnabled(bool(text.strip()))

    def copy_transcription_to_clipboard(self, *, application):
        text = self.widget.text_display.toPlainText() if self.widget.text_display else ""
        if text.strip():
            application.clipboard().setText(text)
            self.widget.status_changed.emit("Transcription copied.")

    def open_speaker_manager(self, *, dialog_cls, message_box):
        text = self.widget.text_display.toPlainText()
        speakers = find_speaker_labels(text)
        if not speakers:
            message_box.information(self.widget, "Info", "No speakers found in the text.")
            return
        dialog = dialog_cls(speakers, self.widget, known_speakers=self.widget.db.get_all_speakers())
        if dialog.exec():
            self.widget.text_display.setText(apply_speaker_mapping(text, dialog.get_mapping()))
            self.widget.save_all_changes()

    def retranscribe_recording(self):
        if self.widget.current_recording_path:
            self.widget.start_transcription(self.widget.current_recording_path)

    def cleanup(self, *, qurl):
        self.widget.stop_audio()
        self.widget.player.setSource(qurl())
        for attribute in ("transcriber_thread", "ai_thread"):
            self.cleanup_thread(attribute)

    def cleanup_thread(self, attribute):
        thread = getattr(self.widget, attribute, None)
        if not thread:
            return
        try:
            if thread.isRunning():
                thread.requestInterruption(); thread.quit(); thread.wait(3000)
        except Exception:
            pass
        try:
            thread.deleteLater()
        except Exception:
            pass
        setattr(self.widget, attribute, None)

    def clear_thread_ref(self, attribute):
        thread = getattr(self.widget, attribute, None)
        setattr(self.widget, attribute, None)
        if thread:
            thread.deleteLater()
