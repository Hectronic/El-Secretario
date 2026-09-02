"""Widget-level orchestration around the direct transcription flow helpers."""

import logging
import os

from src.ui.recording.rag_indexing import index_transcription_result_after_refresh
from src.ui.recording.state import to_bool
from src.ui.recording.transcription_flow import (
    emit_error_trace,
    emit_finished_trace,
    emit_status_trace,
    persist_direct_transcription_result,
    start_direct_transcription,
)


class RecordingTranscriptionCoordinator:
    """Coordinate widget updates around a direct transcription worker."""

    def __init__(self, widget):
        self.widget = widget

    def set_transcription_config(self, config):
        widget = self.widget
        if not getattr(widget, "model_combo", None):
            return
        if config.get("model"):
            index = widget.model_combo.findText(config["model"])
            if index >= 0:
                widget.model_combo.setCurrentIndex(index)
        if config.get("language") is not None:
            language_label = {None: "Auto", "es": "Spanish", "en": "English"}.get(
                config["language"], "Auto"
            )
            index = widget.lang_combo.findText(language_label)
            if index >= 0:
                widget.lang_combo.setCurrentIndex(index)
        if config.get("diarization") is not None:
            widget.diarization_check.setChecked(config["diarization"])
        if config.get("auto_summarize_after_transcription") is not None:
            widget.auto_summarize_after_transcription = to_bool(
                config["auto_summarize_after_transcription"]
            )

    def start_transcription(
        self,
        audio_path,
        *,
        settings_cls,
        thread_cls,
        preflight_check,
        sound_file_cls,
        message_box,
    ):
        widget = self.widget
        widget.transcriber_thread = start_direct_transcription(
            widget,
            audio_path,
            settings=settings_cls("Hectronic", "Secretario"),
            model_size=widget.model_combo.currentText(),
            language_label=widget.lang_combo.currentText(),
            enable_diarization=widget.diarization_check.isChecked(),
            thread_cls=thread_cls,
            preflight_check=preflight_check,
            sound_file_cls=sound_file_cls,
            message_box=message_box,
        )

    def on_transcription_finished(self, result, *, settings_cls):
        widget = self.widget
        logging.info(
            "Post-transcription checkpoint P1: entered on_transcription_finished record_id=%s",
            widget.current_record_id,
        )
        emit_finished_trace(widget.summary_task_queue, widget.current_record_id, result)
        widget.status_changed.emit("Saved.")
        widget.progress_changed.emit(-2)
        widget.retranscribe_btn.setEnabled(True)
        text = result["text"]
        widget.text_display.setText(text)
        widget._update_transcription_actions()

        filename = os.path.basename(widget.current_recording_path)
        widget.current_record_id = persist_direct_transcription_result(
            widget.db, widget.current_record_id, filename, result
        )
        widget.load_record(widget.current_record_id)
        widget.recording_saved.emit()
        if widget.auto_summarize_after_transcription and text.strip():
            widget._enqueue_post_transcription_ai_tasks()
        index_transcription_result_after_refresh(
            rag=widget.rag,
            db=widget.db,
            settings=settings_cls("Hectronic", "Secretario"),
            record_id=widget.current_record_id,
            title=filename,
            date_label=widget.date_label.text(),
            emit_status=widget.status_changed.emit,
        )

    def on_transcription_error(self, error, *, message_box):
        widget = self.widget
        emit_error_trace(widget.summary_task_queue, widget.current_record_id, error)
        widget.status_changed.emit("Failed.")
        widget.progress_changed.emit(-2)
        widget.retranscribe_btn.setEnabled(True)
        message_box.critical(widget, "Error", error)

    def on_status_update(self, message):
        widget = self.widget
        widget.status_changed.emit(message)
        emit_status_trace(widget.summary_task_queue, widget.current_record_id, message)
