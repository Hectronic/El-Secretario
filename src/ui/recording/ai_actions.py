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
# along with this program.  See <https://www.gnu.org/licenses/>.

from src.ui.recording.state import fallback_record_title

QUEUE_REQUIRED_MESSAGE = "Summary and task extraction must run through the central queue."
AUTO_SUMMARY_QUEUE_REQUIRED_MESSAGE = "Automatic summary requires the central queue to be available."


def compose_record_ai_text(db, transcription, notes):
    return db.compose_ai_text(transcription, notes)


def has_ai_tasks_for_record(db, record_id):
    if not record_id:
        return False
    try:
        return db.has_ai_tasks_for_record(record_id)
    except Exception:
        return False


def extract_tasks_button_text(db, record_id):
    return "Re-extract Tasks (AI)" if has_ai_tasks_for_record(db, record_id) else "Extract Tasks (AI)"


def enqueue_recording_summary(queue, record_id, text, title):
    queue.enqueue_recording_summary(record_id, text, title, source="recording")


def enqueue_task_extraction(queue, db, record_id, text, tags, title):
    force_reextract = has_ai_tasks_for_record(db, record_id)
    if force_reextract:
        db.delete_ai_tasks_by_record(record_id)
    queue.enqueue_task_extraction(
        record_id,
        text,
        tags,
        title,
        force=force_reextract,
        source="recording",
    )
    return force_reextract


def enqueue_post_transcription_summary(queue, record_id, text, title):
    if not text.strip():
        return False
    if not queue:
        return False
    enqueue_recording_summary(queue, record_id, text, title)
    return True


def configure_legacy_ai_thread(widget, assistant_cls, task_type, text):
    widget.status_changed.emit(f"Running {task_type}...")
    widget.progress_changed.emit(-1)
    thread = assistant_cls("", task_type, text)
    thread.task_completed.connect(widget.on_ai_finished)
    thread.error.connect(widget.on_ai_error)
    thread.finished.connect(widget._clear_ai_thread_ref)
    thread.error.connect(widget._clear_ai_thread_ref)
    thread.start()
    return thread


def apply_ai_result(widget, task_type, result):
    widget.status_changed.emit("AI Task Done.")
    widget.progress_changed.emit(-2)
    if task_type == "summary":
        widget.summary_display.setText(result)
        widget.db.update_ai_content(widget.current_record_id, summary=result)
        widget.tabs.setCurrentWidget(widget.summary_display)
    elif task_type == "task_extraction":
        widget.tasks_widget.refresh()
        refresh_global_tasks_sidebar(widget.application_top_level_widgets())


def refresh_global_tasks_sidebar(top_level_widgets):
    for widget in top_level_widgets:
        if hasattr(widget, "refresh_tasks_sidebar"):
            widget.refresh_tasks_sidebar()


def record_title_for_actions(record_id, title_text):
    return fallback_record_title(record_id, title_text)
