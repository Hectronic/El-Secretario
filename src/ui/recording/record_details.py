"""Loading and persistence orchestration for recording detail widgets."""

from PyQt6.QtCore import QSettings

from src.ui.recording.rag_indexing import index_saved_record_changes
from src.ui.recording.state import record_has_ai_text


class RecordingDetailsCoordinator:
    """Synchronize a recording row with the detail widget without owning its UI."""

    def __init__(self, widget):
        self.widget = widget

    def load_record(self, record_id):
        record = self.widget.db.fetch_record(record_id)
        if not record:
            return
        if self.widget.audio_edit_mode:
            self._load_audio_editor_record(record)
            return
        self._load_record_detail(record)

    def _load_audio_editor_record(self, record):
        widget = self.widget
        widget.current_record_id = record["id"]
        widget.current_recording_path = widget._recording_audio_path(record)
        widget._configure_audio_edit_bounds(record["duration"])
        can_edit_audio = widget._set_record_audio_source(record)
        widget._set_audio_edit_enabled(can_edit_audio)
        widget._set_dirty(False)

    def _load_record_detail(self, record):
        widget = self.widget
        widget._suppress_dirty_tracking = True
        try:
            widget.current_record_id = record["id"]
            widget.text_display.setText(record["transcription"])
            widget.notes_display.setText(record.get("recording_notes") or "")
            widget.summary_display.setText(record["summary"] if record["summary"] else "")
            widget.title_input.setText(record["title"] if record["title"] else "")
            widget.title_input.setEnabled(True)
            widget.tags_input.setText(record["tags"] if record["tags"] else "")
            widget.tags_input.setEnabled(True)
            widget.is_diarized_check_meta.setChecked(bool(record["is_diarized"]))
            widget.is_diarized_check_meta.setEnabled(True)
            widget.date_label.setText(record["created_at"])
            widget.duration_label.setText(f"{record['duration']:.1f}s")
            widget._configure_audio_edit_bounds(record["duration"])

            has_text = record_has_ai_text(record)
            widget.summarize_btn.setEnabled(has_text)
            widget.extract_tasks_btn.setEnabled(has_text)
            widget._update_extract_tasks_button()
            widget.rename_speakers_btn.setEnabled(has_text)
            widget._update_transcription_actions()

            widget.current_recording_path = widget._recording_audio_path(record)
            can_edit_audio = widget._set_record_audio_source(record)
            widget.tasks_widget.record_id = widget.current_record_id
            widget.tasks_widget.refresh()
            widget.ask_meeting_btn.setEnabled(True)
            widget.edit_audio_btn.setEnabled(can_edit_audio)
            widget._set_audio_edit_enabled(can_edit_audio)
            widget._set_dirty(False)
        finally:
            widget._suppress_dirty_tracking = False

    def save_all_changes(self):
        widget = self.widget
        if not widget.current_record_id:
            return False

        title = widget.title_input.text().strip()
        transcription = widget.text_display.toPlainText()
        notes = widget.notes_display.toPlainText().strip()
        tags = widget.tags_input.text().strip()
        is_diarized = widget.is_diarized_check_meta.isChecked()
        widget.db.update_title(widget.current_record_id, title)
        widget.db.update_transcription(
            widget.current_record_id, transcription, is_diarized=is_diarized
        )
        widget.db.update_recording_notes(widget.current_record_id, notes)
        widget.db.update_tags(widget.current_record_id, tags)
        index_saved_record_changes(
            rag=widget.rag,
            db=widget.db,
            settings=QSettings("Hectronic", "Secretario"),
            record_id=widget.current_record_id,
            transcription=transcription,
            notes=notes,
            title=title,
            date_label=widget.date_label.text(),
            tags=tags,
        )
        widget._set_dirty(False)
        widget.recording_saved.emit()
        widget.status_changed.emit("Saved.")
        return True
