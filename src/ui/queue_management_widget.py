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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QListWidgetItem, QPushButton, QLabel, QMessageBox, QProgressBar)
from src.app.summary_queue.actions import QueueActionCoordinator
from src.app.summary_queue.presentation import (
    build_queue_management_snapshot,
    format_history_entry,
    format_task_display,
    map_progress_state,
    normalize_status_message,
)

class QueueManagementWidget(QWidget):
    """Operational view for the central background-task queue.

    The widget treats ``SummaryTaskQueueManager`` as the source of truth and
    only renders snapshots: current task, wait/retry state, live progress,
    pending work and in-session history. Keeping formatting here avoids each
    producer inventing its own status presentation.
    """
    
    def __init__(self, task_queue, parent=None):
        super().__init__(parent)
        self.task_queue = task_queue
        self.actions = QueueActionCoordinator(task_queue)
        
        self.init_ui()
        self.refresh_queue()
        
        # Connect to queue signals to refresh automatically
        self.task_queue.queue_changed.connect(lambda count, running: self.refresh_queue())
        self.task_queue.task_started.connect(lambda task, remaining: self.refresh_queue())
        self.task_queue.task_finished.connect(lambda task: self.refresh_queue())
        self.task_queue.wait_state_changed.connect(lambda *_: self.refresh_queue())
        self.task_queue.task_status_update.connect(self._on_status_update)
        self.task_queue.task_progress.connect(self._on_progress_update)
        self.task_queue.task_failed.connect(lambda *_: self.refresh_queue())
        self.task_queue.task_skipped.connect(lambda *_: self.refresh_queue())
        if hasattr(self.task_queue, "history_changed"):
            self.task_queue.history_changed.connect(lambda *_: self.refresh_history())

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Manage Task Queue")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
        layout.addWidget(header)
        
        # Current Task Section
        current_group = QVBoxLayout()
        current_group.addWidget(QLabel("<b>Currently Running:</b>"))
        self.current_task_label = QLabel("None")
        self.current_task_label.setStyleSheet("padding: 10px; background-color: #333; border-radius: 5px; color: #4CAF50;")
        current_group.addWidget(self.current_task_label)

        self.wait_label = QLabel("Wait: none")
        self.wait_label.setStyleSheet("padding: 8px; color: #f5c542;")
        current_group.addWidget(self.wait_label)

        self.live_status_label = QLabel("Status: idle")
        self.live_status_label.setStyleSheet("padding: 8px; color: #90CAF9;")
        current_group.addWidget(self.live_status_label)

        self.live_progress = QProgressBar()
        self.live_progress.setRange(0, 1)
        self.live_progress.setValue(0)
        self.live_progress.setTextVisible(True)
        self.live_progress.setFormat("Idle")
        current_group.addWidget(self.live_progress)

        self.metrics_label = QLabel("Metrics: running=0 pending=0 queued=0 finished=0 failed=0 skipped=0")
        self.metrics_label.setStyleSheet("padding: 8px; color: #B0BEC5; font-size: 12px;")
        current_group.addWidget(self.metrics_label)
        layout.addLayout(current_group)
        
        # Pending Tasks List
        layout.addWidget(QLabel("<b>Pending Tasks:</b>"))
        self.queue_list = QListWidget()
        self.queue_list.setProperty("class", "embedded-list")
        layout.addWidget(self.queue_list)

        # Session History
        layout.addWidget(QLabel("<b>Execution History (Session):</b>"))
        self.history_list = QListWidget()
        self.history_list.setProperty("class", "embedded-list")
        layout.addWidget(self.history_list)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.move_up_btn = QPushButton("↑ Move Up")
        self.move_up_btn.clicked.connect(self._move_up)
        controls_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("↓ Move Down")
        self.move_down_btn.clicked.connect(self._move_down)
        controls_layout.addWidget(self.move_down_btn)
        
        self.remove_btn = QPushButton("🗑 Remove")
        self.remove_btn.setStyleSheet("color: #f44336;")
        self.remove_btn.clicked.connect(self._remove_selected)
        controls_layout.addWidget(self.remove_btn)

        self.stop_current_btn = QPushButton("⏹ Stop Current")
        self.stop_current_btn.clicked.connect(self._stop_current)
        controls_layout.addWidget(self.stop_current_btn)
        
        controls_layout.addStretch()
        
        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self._clear_all)
        controls_layout.addWidget(self.clear_all_btn)

        self.stop_all_btn = QPushButton("Stop All")
        self.stop_all_btn.setStyleSheet("color: #f44336;")
        self.stop_all_btn.clicked.connect(self._stop_all)
        controls_layout.addWidget(self.stop_all_btn)
        
        layout.addLayout(controls_layout)
        
        description = QLabel(
            "Tasks are processed sequentially. You can reorder pending tasks or remove them from the queue."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: gray; font-size: 13px;")
        layout.addWidget(description)

    def _format_task_display(self, task):
        return format_task_display(task)

    def refresh_queue(self):
        current = self.task_queue.get_current_task()
        is_waiting, seconds_left, desc = self.task_queue.get_wait_state()
        pending = self.task_queue.get_queue_list()
        history = self.task_queue.get_session_history() if hasattr(self.task_queue, "get_session_history") else []
        runtime_stats = self.task_queue.get_runtime_stats() if hasattr(self.task_queue, "get_runtime_stats") else None
        snapshot = build_queue_management_snapshot(
            current_task=current,
            pending_tasks=pending,
            is_waiting=is_waiting,
            seconds_left=seconds_left,
            wait_description=desc,
            history_entries=history,
            runtime_stats=runtime_stats,
            fallback_running=1 if current else 0,
            fallback_pending=len(pending),
        )

        # 1. Update current/wait state labels
        self.current_task_label.setText(snapshot["current_label"])
        if snapshot["has_current_task"]:
            if self.live_status_label.text().strip().lower() == "status: idle":
                self.live_status_label.setText("Status: running...")
        else:
            self.live_status_label.setText("Status: idle")
            self.live_progress.setRange(0, 1)
            self.live_progress.setValue(0)
            self.live_progress.setFormat("Idle")
        self.wait_label.setText(snapshot["wait_label"])

        self.metrics_label.setText(snapshot["metrics_label"])
            
        # 2. Update pending list
        # Block signals to avoid issues while refreshing
        self.queue_list.blockSignals(True)
        
        # Save selection
        current_row = self.queue_list.currentRow()
        
        self.queue_list.clear()
        for label in snapshot["pending_labels"]:
            item = QListWidgetItem(label)
            self.queue_list.addItem(item)
            
        # Restore selection
        if current_row < self.queue_list.count():
            self.queue_list.setCurrentRow(current_row)
            
        self.queue_list.blockSignals(False)
        self._apply_history_labels(snapshot["history_labels"])

    def refresh_history(self):
        history = self.task_queue.get_session_history() if hasattr(self.task_queue, "get_session_history") else []
        labels = [format_history_entry(entry) for entry in history]
        self._apply_history_labels(labels)

    def _apply_history_labels(self, labels):
        self.history_list.clear()
        for label in labels:
            self.history_list.addItem(QListWidgetItem(label))

    def _format_history_entry(self, entry):
        return format_history_entry(entry)

    def _on_status_update(self, message):
        status_text = normalize_status_message(message)
        if not status_text:
            return
        self.live_status_label.setText(status_text)

    def _on_progress_update(self, value):
        mapped = map_progress_state(value)
        if mapped["mode"] == "ignore":
            return
        self.live_progress.setRange(int(mapped["min"]), int(mapped["max"]))
        self.live_progress.setValue(int(mapped["value"]))
        self.live_progress.setFormat(str(mapped["format"]))

    def _move_up(self):
        row = self.queue_list.currentRow()
        new_row = self.actions.move_up(row)
        if new_row != row:
            self.queue_list.setCurrentRow(new_row)

    def _move_down(self):
        row = self.queue_list.currentRow()
        new_row = self.actions.move_down(row, self.queue_list.count())
        if new_row != row:
            self.queue_list.setCurrentRow(new_row)

    def _remove_selected(self):
        row = self.queue_list.currentRow()
        self.actions.remove_selected(row)

    def _clear_all(self):
        if QMessageBox.question(self, "Clear Queue", "Remove all pending tasks?") == QMessageBox.StandardButton.Yes:
            self.actions.clear_pending()

    def _stop_current(self):
        self.actions.stop_current()
        self.refresh_queue()

    def _stop_all(self):
        if QMessageBox.question(self, "Stop All", "Stop current task and clear all pending tasks?") == QMessageBox.StandardButton.Yes:
            self.actions.stop_all()
            self.refresh_queue()
