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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Main-window presentation and synchronization for summary queue activity."""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QPushButton, QProgressBar

from src.ui.calendar_widget import CalendarWidget
from src.ui.queue_management_widget import QueueManagementWidget
from src.ui.recording_widget import RecordingWidget
from src.ui.summary_viewer import SummaryViewerWidget


class SummaryQueueStatusCoordinator:
    """Keep queue status widgets and affected main-window views in sync."""

    def __init__(self, window):
        self.window = window

    def setup_status_bar(self):
        window = self.window
        status = window.statusBar()
        window.task_status_label = QLabel("Summary queue idle.")
        window.task_status_label.setStyleSheet("padding-right: 8px;")
        window.task_metrics_label = QLabel("Q r0 p0 f0 e0 s0")
        window.task_metrics_label.setStyleSheet("padding-right: 8px; color: #90A4AE;")

        window.open_queue_btn = QPushButton("📋 View Queue")
        window.open_queue_btn.setFlat(True)
        window.open_queue_btn.setStyleSheet(
            "color: #2196F3; text-decoration: underline; font-weight: bold;"
        )
        window.open_queue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.open_queue_btn.clicked.connect(self.open_queue_manager_tab)

        window.task_queue_progress = QProgressBar()
        window.task_queue_progress.setFixedWidth(180)
        window.task_queue_progress.setTextVisible(False)
        window.task_queue_progress.setRange(0, 1)
        window.task_queue_progress.setValue(0)

        status.addPermanentWidget(window.task_status_label, 1)
        status.addPermanentWidget(window.task_metrics_label)
        status.addPermanentWidget(window.open_queue_btn)
        status.addPermanentWidget(window.task_queue_progress)
        self.refresh_task_metrics()

    def open_queue_manager_tab(self):
        """Open the task queue management tab, or select the existing one."""
        window = self.window
        for index in range(window.central_tabs.count()):
            widget = window.central_tabs.widget(index)
            if isinstance(widget, QueueManagementWidget):
                window.central_tabs.setCurrentIndex(index)
                return

        queue_widget = QueueManagementWidget(window.summary_task_queue)
        index = window.central_tabs.addTab(queue_widget, "📋 Task Queue")
        window.central_tabs.setCurrentIndex(index)

    def connect_task_queue_signals(self):
        queue = self.window.summary_task_queue
        queue.task_enqueued.connect(self.on_summary_task_enqueued)
        queue.task_started.connect(self.on_summary_task_started)
        queue.task_finished.connect(self.on_summary_task_finished)
        queue.task_failed.connect(self.on_summary_task_failed)
        queue.task_skipped.connect(self.on_summary_task_skipped)
        queue.queue_changed.connect(self.on_summary_queue_changed)
        queue.task_progress.connect(self.handle_progress)
        queue.task_status_update.connect(self.handle_status_message)
        if hasattr(queue, "history_changed"):
            queue.history_changed.connect(lambda *_: self.refresh_task_metrics())

    def refresh_task_metrics(self):
        queue = self.window.summary_task_queue
        try:
            stats = queue.get_runtime_stats()
        except Exception:
            stats = None
        if not isinstance(stats, dict):
            pending = int(getattr(queue, "pending_count", 0) or 0)
            running = 1 if getattr(queue, "is_running", False) else 0
            self.window.task_metrics_label.setText(f"Q r{running} p{pending} f0 e0 s0")
            return
        self.window.task_metrics_label.setText(
            "Q "
            f"r{int(stats.get('running', 0))} "
            f"p{int(stats.get('pending', 0))} "
            f"f{int(stats.get('finished', 0))} "
            f"e{int(stats.get('failed', 0))} "
            f"s{int(stats.get('skipped', 0))}"
        )

    @staticmethod
    def format_task_name(task):
        task_type = task.get("type")
        if task_type == "summary":
            return f"Recording: {task.get('title', 'Unknown')}"
        if task_type == "task_extraction":
            return f"Tasks: {task.get('title', 'Unknown')}"
        if task_type == "transcription":
            return f"Transcribing: {task.get('title', 'Unknown')}"
        if task_type == "weekly_summary":
            return f"Week: {task.get('date', 'Unknown')}"
        if task_type == "rag_reindex":
            if task.get("reindex_scope", "all") == "missing":
                return "RAG Reindex (Missing)"
            return "RAG Reindex (All)"

        date = task.get("date", "unknown date")
        tags_filter = task.get("tags_filter")
        if tags_filter:
            return f"Day: {date} [{tags_filter}]"
        return f"Day: {date}"

    def on_summary_task_enqueued(self, task, position):
        self.window.task_status_label.setText(
            f"Queued task: {self.format_task_name(task)} (#{position} in queue)"
        )
        self.refresh_task_metrics()

    def on_summary_task_started(self, task, remaining_pending):
        window = self.window
        window.regen_worker = window.summary_task_queue.current_worker
        window.task_status_label.setText(
            f"Running: {self.format_task_name(task)} "
            f"({window.summary_task_queue.pending_count} pending)"
        )
        self.refresh_task_metrics()

    def on_summary_task_finished(self, task):
        window = self.window
        try:
            window.regen_worker = window.summary_task_queue.current_worker
            task_type = task.get("type")

            if task_type == "summary":
                self._refresh_recording_tab(task.get("record_id"), include_summary=True)
                window.request_sidebar_reload(include_history=True)
            elif task_type == "task_extraction":
                self._refresh_recording_tab(task.get("record_id"), include_tasks=True)
                for index in range(window.central_tabs.count()):
                    widget = window.central_tabs.widget(index)
                    if isinstance(widget, SummaryViewerWidget):
                        widget._load_daily_tasks()
                window.refresh_tasks_sidebar()
            elif task_type == "daily_summary":
                date = task.get("date")
                if date:
                    self.refresh_daily_summary_viewers(date, task.get("tags_filter"))
                    window.request_sidebar_reload(include_history=True)
            elif task_type == "weekly_summary":
                window.request_sidebar_reload(include_history=True)
                for index in range(window.central_tabs.count()):
                    widget = window.central_tabs.widget(index)
                    try:
                        if isinstance(widget, CalendarWidget):
                            widget.update_summary_view()
                    except (RuntimeError, AttributeError):
                        continue
            elif task_type == "rag_reindex":
                window.request_sidebar_reload(include_history=True)

            window.task_status_label.setText(f"Finished: {self.format_task_name(task)}")
            self.refresh_task_metrics()
        except Exception as error:
            logging.error("Error in summary queue completion UI: %s", error, exc_info=True)

    def _refresh_recording_tab(self, record_id, **refresh_options):
        for index in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(index)
            try:
                if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                    widget.refresh_from_background_queue(**refresh_options)
            except (RuntimeError, AttributeError):
                continue

    def on_summary_task_failed(self, task, error_msg):
        try:
            self.window.regen_worker = self.window.summary_task_queue.current_worker
            self.window.task_status_label.setText(
                f"Regeneration failed for {self.format_task_name(task)}: {error_msg}"
            )
            self.refresh_task_metrics()
        except Exception:
            pass

    def on_summary_task_skipped(self, task, reason):
        self.window.task_status_label.setText(
            f"Skipped regeneration for {self.format_task_name(task)}: {reason}"
        )
        self.refresh_task_metrics()

    def on_summary_queue_changed(self, pending_count, is_running):
        window = self.window
        window.refresh_tasks_sidebar()
        self.refresh_task_metrics()
        if is_running:
            window.task_queue_progress.setRange(0, 0)
            window.task_queue_progress.setVisible(True)
            return

        window.task_queue_progress.setRange(0, 1)
        window.task_queue_progress.setValue(0 if pending_count == 0 else 1)
        if pending_count == 0:
            window.task_status_label.setText("Summary queue idle.")

    def handle_status_message(self, message):
        label = self.window.__dict__.get("task_status_label")
        if label is None:
            try:
                self.window.statusBar().showMessage(str(message or ""), 5000)
            except Exception:
                pass
            return

        if not self.window.summary_task_queue.is_running:
            label.setText(message)

    def handle_progress(self, value):
        window = self.window
        if window.summary_task_queue.is_running:
            return

        if value == -1:
            window.task_queue_progress.setRange(0, 0)
            window.task_queue_progress.setVisible(True)
        elif value == -2:
            window.task_queue_progress.setRange(0, 1)
            window.task_queue_progress.setValue(0)
            window.task_queue_progress.setVisible(True)
        else:
            window.task_queue_progress.setRange(0, 100)
            window.task_queue_progress.setValue(value)
            window.task_queue_progress.setVisible(True)

    def refresh_daily_summary_viewers(self, date, tags_filter):
        window = self.window
        for index in range(window.central_tabs.count()):
            widget = window.central_tabs.widget(index)
            if not isinstance(widget, SummaryViewerWidget):
                continue
            summary_data = widget.summary_data
            if summary_data.get("type") != "daily":
                continue
            same_date = summary_data.get("date") == date
            same_tags = (summary_data.get("tags_filter") or "") == (tags_filter or "")
            if not (same_date and same_tags):
                continue
            new_summary_data = window.db.get_daily_summary_details(date, tags_filter or None)
            if new_summary_data:
                new_summary_data["type"] = "daily"
                widget.update_content(new_summary_data)
