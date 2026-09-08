"""Summary generation orchestration for CalendarWidget."""

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from src.ai_assistant import AIAssistant
from src.summary_generator import SummaryGenerator, get_pending_summary_counts


def on_generate_daily_summary_clicked(widget):
    if len(widget.selected_dates) != 1:
        QMessageBox.warning(widget, "Select One Date", "Please select exactly one date.")
        return
        
    date = list(widget.selected_dates)[0]
    date_str = date.toString("yyyy-MM-dd")
    tags = widget.get_selected_tags()
    tags_filter = widget.get_tags_filter_str()
    
    if widget.summary_task_queue:
        widget.summary_task_queue.enqueue_daily_summary({
            "date": date_str,
            "tags_filter": tags_filter,
            "source": "calendar",
        })
        return

    recordings = widget.db.fetch_by_dates([date_str], tags)
    if not recordings:
        QMessageBox.warning(widget, "No Recordings", "No recordings found.")
        return
        
    full_text = ""
    for rec in recordings:
        full_text += f"\n\n--- Recording: {rec['title'] or 'Untitled'} ({rec['created_at']}) ---\n"
        full_text += rec['transcription'] or ""
        
    if not full_text.strip():
        QMessageBox.warning(widget, "No Content", "No transcription content.")
        return
        
    widget.progress = QProgressDialog("Generating Daily Summary...", "Cancel", 0, 0, widget)
    widget.progress.setWindowModality(Qt.WindowModality.WindowModal)
    widget.progress.show()
    
    settings = QSettings("Hectronic", "Secretario")
    from src.ai_provider import validate_ai_provider_config
    is_valid, error_msg = validate_ai_provider_config(settings)
    if not is_valid:
        widget.progress.close()
        QMessageBox.critical(widget, "Error", error_msg)
        return
        
    widget.pending_daily_key = (date_str, widget.get_tags_filter_str())
    widget.worker = AIAssistant("", "daily_summary", full_text)
    widget.worker.task_completed.connect(widget.on_summary_finished)
    widget.worker.error.connect(widget.on_summary_error)
    widget.worker.start()



def on_generate_summary_clicked(widget):
    if not widget.current_week_monday:
        QMessageBox.warning(widget, "No Week Selected", "No week context.")
        return
        
    week_sunday = widget.current_week_monday.addDays(6).toString("yyyy-MM-dd")
    week_dates = [widget.current_week_monday.addDays(i).toString("yyyy-MM-dd") for i in range(7)]
    tags = widget.get_selected_tags()
    recordings_for_summary = widget.db.fetch_by_dates(week_dates, tags)
    
    if not recordings_for_summary:
        QMessageBox.warning(widget, "No Recordings", "No recordings found for the week.")
        return

    full_text = ""
    for rec in recordings_for_summary:
        full_text += f"\n\n--- Recording: {rec['title'] or 'Untitled'} ({rec['created_at']}) ---\n"
        full_text += rec['transcription'] or ""

    if not full_text.strip():
        QMessageBox.warning(widget, "No Content", "No transcription content.")
        return

    if widget.summary_task_queue:
        tags_filter = widget.get_tags_filter_str() or ""
        widget.summary_task_queue.enqueue_weekly_summary(week_sunday, full_text, tags_filter, source="calendar")
        return

    widget.progress = QProgressDialog("Generating Weekly Summary...", "Cancel", 0, 0, widget)
    widget.progress.setWindowModality(Qt.WindowModality.WindowModal)
    widget.progress.show()

    settings = QSettings("Hectronic", "Secretario")
    from src.ai_provider import validate_ai_provider_config
    is_valid, error_msg = validate_ai_provider_config(settings)
    if not is_valid:
        widget.progress.close()
        QMessageBox.critical(widget, "Error", error_msg)
        return

    widget.pending_summary_key = widget.get_summary_key()
    widget.worker = AIAssistant("", "weekly_summary", full_text)
    widget.worker.task_completed.connect(widget.on_summary_finished)
    widget.worker.error.connect(widget.on_summary_error)
    widget.worker.start()



def on_generate_pending_clicked(widget):
    tags_filter = widget.get_tags_filter_str()
    pending_daily, pending_weekly = get_pending_summary_counts(tags_filter)
    
    if pending_daily == 0 and pending_weekly == 0:
        QMessageBox.information(widget, "All Done", "No pending summaries.")
        return
        
    msg = f"Found {pending_daily} days and {pending_weekly} weeks without summaries.\n\nGenerate all?"
    reply = QMessageBox.question(widget, "Generate Pending", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        return
        
    widget.pending_progress = QProgressDialog("Generating pending summaries...", "Cancel", 0, pending_daily + pending_weekly, widget)
    widget.pending_progress.setWindowModality(Qt.WindowModality.WindowModal)
    widget.pending_progress.show()
    
    widget.summary_generator = SummaryGenerator(True, True, tags_filter, parent=widget)
    widget.summary_generator.progress.connect(widget.on_pending_progress)
    widget.summary_generator.finished.connect(widget.on_pending_finished)
    widget.summary_generator.error.connect(widget.on_pending_error)
    widget.pending_progress.canceled.connect(widget.summary_generator.cancel)
    widget.summary_generator.start()



def on_pending_progress(widget, current, total):
    if hasattr(widget, 'pending_progress'):
        widget.pending_progress.setValue(current)



def on_pending_finished(widget, daily_count, weekly_count):
    if hasattr(widget, 'pending_progress'):
        widget.pending_progress.close()
    QMessageBox.information(widget, "Complete", f"Generated {daily_count} daily and {weekly_count} weekly summaries.")
    widget.update_daily_summary_view()
    widget.update_summary_view()



def on_pending_error(widget, error_msg):
    if hasattr(widget, 'pending_progress'):
        widget.pending_progress.close()
    QMessageBox.critical(widget, "Error", f"Failed: {error_msg}")



def on_summary_finished(widget, task_type, result):
    if hasattr(widget, 'progress'):
        widget.progress.close()
    
    if task_type == "weekly_summary":
        if widget.pending_summary_key:
            week_str, tags_tuple = widget.pending_summary_key
            tags_filter = ",".join(tags_tuple) if tags_tuple else None
            widget.db.save_weekly_summary(week_str, result, tags_filter)
            if widget.pending_summary_key == widget.get_summary_key():
                widget.update_summary_view()
        widget.pending_summary_key = None
        
    elif task_type == "daily_summary":
        if widget.pending_daily_key:
            date_str, tags_filter = widget.pending_daily_key
            widget.db.save_daily_summary(date_str, result, tags_filter)
            if len(widget.selected_dates) == 1:
                current_date = list(widget.selected_dates)[0].toString("yyyy-MM-dd")
                if current_date == date_str:
                    widget.update_daily_summary_view()
        widget.pending_daily_key = None



def on_summary_error(widget, error_msg):
    if hasattr(widget, 'progress'):
        widget.progress.close()
    widget.pending_summary_key = None
    widget.pending_daily_key = None
    QMessageBox.critical(widget, "Error", f"Failed: {error_msg}")

