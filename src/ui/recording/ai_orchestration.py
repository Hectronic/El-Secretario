"""Widget-level orchestration for recording AI actions and queue refreshes."""

from src.ui.recording.ai_actions import (
    AUTO_SUMMARY_QUEUE_REQUIRED_MESSAGE,
    QUEUE_REQUIRED_MESSAGE,
    apply_ai_result,
    compose_record_ai_text,
    configure_legacy_ai_thread,
    enqueue_post_transcription_summary,
    enqueue_recording_summary,
    enqueue_task_extraction,
    extract_tasks_button_text,
)
from src.ui.recording.state import fallback_record_title


class RecordingAiCoordinator:
    def __init__(self, widget):
        self.widget = widget

    def run_ai_task(
        self, task_type, *, settings_cls, assistant_cls, validate_provider, message_box
    ):
        widget = self.widget
        text = compose_record_ai_text(
            widget.db, widget.text_display.toPlainText(), widget.notes_display.toPlainText()
        )
        if not text:
            return
        title = fallback_record_title(widget.current_record_id, widget.title_input.text())
        if widget.summary_task_queue:
            if task_type == "summary":
                enqueue_recording_summary(widget.summary_task_queue, widget.current_record_id, text, title)
                return
            if task_type == "task_extraction":
                force_reextract = enqueue_task_extraction(
                    widget.summary_task_queue,
                    widget.db,
                    widget.current_record_id,
                    text,
                    widget.tags_input.text(),
                    title,
                )
                if force_reextract:
                    widget.tasks_widget.refresh()
                    self.update_extract_tasks_button()
                return
        elif task_type in {"summary", "task_extraction"}:
            message_box.warning(widget, "Error", QUEUE_REQUIRED_MESSAGE)
            return

        is_valid, error_message = validate_provider(settings_cls("Hectronic", "Secretario"))
        if not is_valid:
            message_box.warning(widget, "Error", error_message)
            return
        if task_type != "clean":
            widget.ai_thread = configure_legacy_ai_thread(widget, assistant_cls, task_type, text)

    def enqueue_post_transcription_ai_tasks(self, *, message_box):
        widget = self.widget
        text = compose_record_ai_text(
            widget.db, widget.text_display.toPlainText(), widget.notes_display.toPlainText()
        )
        title = fallback_record_title(widget.current_record_id, widget.title_input.text())
        if not enqueue_post_transcription_summary(
            widget.summary_task_queue, widget.current_record_id, text, title
        ) and text.strip():
            message_box.warning(widget, "Error", AUTO_SUMMARY_QUEUE_REQUIRED_MESSAGE)

    def on_ai_finished(self, task_type, result):
        apply_ai_result(self.widget, task_type, result)

    def on_ai_error(self, error, *, message_box):
        self.widget.status_changed.emit("AI Task Failed.")
        self.widget.progress_changed.emit(-2)
        message_box.critical(self.widget, "Error", error)

    def update_extract_tasks_button(self):
        widget = self.widget
        widget.extract_tasks_btn.setText(extract_tasks_button_text(widget.db, widget.current_record_id))

    def refresh_from_background_queue(self, include_summary=False, include_tasks=False):
        widget = self.widget
        if not widget.current_record_id:
            return
        if include_summary:
            record = widget.db.fetch_record(widget.current_record_id)
            if isinstance(record, dict):
                widget.summary_display.setText(record.get("summary") or "")
        if include_tasks:
            widget.tasks_widget.refresh()
        self.update_extract_tasks_button()
