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

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QProgressBar, QTextEdit, QMessageBox, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from src.database import DBManager
from src.worker_components.engine import is_transcription_fatal_failure
from src.transcription_options import get_saved_transcription_model

class BatchProcessWidget(QWidget):
    finished = pyqtSignal()
    
    def __init__(self, task_queue=None, parent=None):
        super().__init__(parent)
        self.db = DBManager()
        self.task_queue = task_queue
        self.queue = []
        self.is_processing = False
        self.total_files = 0
        self.processed_count = 0
        self._queued_record_ids = set()
        self._active_batch_tasks = 0
        self._handled_batch_terminal_tasks = set()
        
        self.init_ui()
        self.load_pending()
        if self.task_queue:
            self.task_queue.task_enqueued.connect(self._on_queue_task_enqueued)
            self.task_queue.task_started.connect(self._on_queue_task_started)
            self.task_queue.task_finished.connect(self._on_queue_task_finished)
            self.task_queue.task_failed.connect(self._on_queue_task_failed)
            self.task_queue.task_skipped.connect(self._on_queue_task_skipped)
        else:
            self.start_btn.setEnabled(False)
            self.status_label.setText("Task queue is required for batch processing.")
            self.log("Batch processing disabled: no central task queue available.")
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Batch Processing Pending Recordings")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
        layout.addWidget(header)
        
        # Status Area
        self.status_label = QLabel("Ready to start.")
        self.status_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.status_label)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        self.file_progress_label = QLabel("0/0 files processed")
        layout.addWidget(self.file_progress_label)

        # Pending List
        self.pending_list = QListWidget()
        self.pending_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.pending_list)
        
        # List Controls
        list_btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.clicked.connect(self.load_pending)
        list_btn_layout.addWidget(self.refresh_btn)
        
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_selected)
        list_btn_layout.addWidget(self.remove_btn)

        self.retry_btn = QPushButton("Retry Failed")
        self.retry_btn.clicked.connect(self.retry_failed)
        list_btn_layout.addWidget(self.retry_btn)
        
        layout.addLayout(list_btn_layout)
        
        # Log Area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        
        # Controls
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Processing")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
    def load_pending(self):
        self.queue = self.db.fetch_pending_diarization()
        self.total_files = len(self.queue)
        self.file_progress_label.setText(f"0/{self.total_files} files processed")
        self.log(f"Found {self.total_files} pending recordings.")
        
        self.pending_list.clear()
        for rec in self.queue:
            item = QListWidgetItem(f"{rec['filename']} ({rec['duration']:.1f}s)")
            item.setData(Qt.ItemDataRole.UserRole, rec)
            
            # Highlight errors
            if rec.get('last_error'):
                is_fatal = is_transcription_fatal_failure(rec.get('last_error'))
                label = "SKIPPED" if is_fatal else "FAILED"
                item.setText(f"{label}: {rec['filename']} (Attempts: {rec.get('processing_attempts')})")
                item.setBackground(Qt.GlobalColor.lightGray if is_fatal else Qt.GlobalColor.red)
                item.setForeground(Qt.GlobalColor.black if is_fatal else Qt.GlobalColor.white)
                item.setToolTip(rec['last_error'])
                
            self.pending_list.addItem(item)
        
        if self.total_files == 0:
            self.start_btn.setEnabled(False)
            self.status_label.setText("No pending recordings found.")
        else:
            self.start_btn.setEnabled(True)
            self.status_label.setText("Ready to start.")
        if not self.task_queue:
            self.start_btn.setEnabled(False)
            self.status_label.setText("Task queue is required for batch processing.")

    def remove_selected(self):
        selected_items = self.pending_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            rec = item.data(Qt.ItemDataRole.UserRole)
            # Remove from queue
            self.queue = [r for r in self.queue if r['id'] != rec['id']]
            # Remove from list
            self.pending_list.takeItem(self.pending_list.row(item))
            
        self.total_files = len(self.queue)
        self.file_progress_label.setText(f"{self.processed_count}/{self.total_files} files processed")
        self.log(f"Removed {len(selected_items)} items from queue.")
            
    def log(self, message):
        self.log_text.append(message)
        
    def start_processing(self):
        if not self.task_queue:
            self.log("Batch processing requires the central queue.")
            self.status_label.setText("Task queue is required for batch processing.")
            return

        if not self.queue:
            return

        self.is_processing = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.processed_count = 0
        self._queued_record_ids.clear()
        self._active_batch_tasks = 0
        self._handled_batch_terminal_tasks.clear()

        enqueued = 0
        for rec in self.queue:
            success = self.task_queue.enqueue_transcription(
                rec["id"],
                os.path.join(os.getcwd(), "recordings", rec["filename"]),
                model_size=get_saved_transcription_model(QSettings("Hectronic", "Secretario")),
                language=None,
                diarization=True,
                title=rec.get("filename") or f"Recording {rec['id']}",
                source="batch_process",
            )
            if success:
                enqueued += 1
                self._queued_record_ids.add(rec["id"])
                self._set_current_item_status(rec["id"], f"Queued: {rec['filename']}")

        self.total_files = len(self._queued_record_ids)
        self.file_progress_label.setText(f"Queued {self.total_files} files for the central queue")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Queued in central queue")
        self.status_label.setText(f"Queued {enqueued} recordings in the central queue.")
        self.log(f"Queued {enqueued} recordings in the central queue.")
        if enqueued == 0:
            self.is_processing = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("%p%")
            self.file_progress_label.setText("0/0 files processed")

    def _on_queue_task_enqueued(self, task, _queue_position):
        if task.get("source") != "batch_process":
            return
        if task.get("type") not in {"transcription", "summary", "task_extraction"}:
            return
        self._active_batch_tasks += 1

    def _batch_task_token(self, task):
        return (
            task.get("type"),
            task.get("record_id"),
            task.get("date"),
            task.get("title"),
            task.get("source"),
        )

    def _register_batch_terminal_task_once(self, task) -> bool:
        if task.get("source") != "batch_process":
            return False
        if task.get("type") not in {"transcription", "summary", "task_extraction"}:
            return False
        token = self._batch_task_token(task)
        if token in self._handled_batch_terminal_tasks:
            return False
        self._handled_batch_terminal_tasks.add(token)
        return True

    def _set_current_item_status(self, record_id, text, background=None):
        item = self._find_item_by_record_id(record_id)
        if not item:
            return
        item.setText(text)
        if background is not None:
            item.setBackground(background)

    def _update_file_progress(self):
        total = max(self.total_files, 1)
        self.file_progress_label.setText(f"{self.processed_count}/{self.total_files} files processed")
        self.progress_bar.setValue(int((self.processed_count / total) * 100))

    def _find_item_by_record_id(self, record_id):
        for i in range(self.pending_list.count()):
            item = self.pending_list.item(i)
            rec = item.data(Qt.ItemDataRole.UserRole)
            if rec and rec.get("id") == record_id:
                return item
        return None

    def _finish_queue_mode_if_done(self):
        if self._active_batch_tasks > 0:
            return
        self.is_processing = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Batch processing finished.")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("%p%")
        self.file_progress_label.setText(f"{self.processed_count}/{self.total_files} files processed")
        self.log("All done.")
        QMessageBox.information(self, "Done", "Batch processing completed.")

    def _on_queue_task_started(self, task, _remaining_pending):
        if not self.is_processing or task.get("source") != "batch_process" or task.get("type") != "transcription":
            return
        record_id = task.get("record_id")
        if record_id is None:
            return
        self.current_record = {"id": record_id, "filename": task.get("title") or f"Recording {record_id}"}
        self.current_item = self._find_item_by_record_id(record_id)
        if self.current_item:
            self.current_item.setBackground(Qt.GlobalColor.yellow)
            self.current_item.setText(f"Processing: {self.current_record['filename']}...")
        self.status_label.setText(f"Processing: {self.current_record['filename']}")

    def _on_queue_task_finished(self, task):
        if task.get("source") != "batch_process":
            return
        first_terminal_event = self._register_batch_terminal_task_once(task)
        if first_terminal_event and self._active_batch_tasks > 0:
            self._active_batch_tasks -= 1
        record_id = task.get("record_id")
        if first_terminal_event and task.get("type") == "transcription" and record_id in self._queued_record_ids:
            self._queued_record_ids.discard(record_id)
            self.processed_count += 1
            self._update_file_progress()
            self._set_current_item_status(record_id, f"Finished: {task.get('title') or f'Recording {record_id}'}")
        self._finish_queue_mode_if_done()

    def _on_queue_task_failed(self, task, error_msg):
        if task.get("source") != "batch_process":
            return
        first_terminal_event = self._register_batch_terminal_task_once(task)
        if first_terminal_event and self._active_batch_tasks > 0:
            self._active_batch_tasks -= 1
        record_id = task.get("record_id")
        if first_terminal_event and task.get("type") == "transcription" and record_id in self._queued_record_ids:
            self._queued_record_ids.discard(record_id)
            label = "SKIPPED" if is_transcription_fatal_failure(error_msg) else "FAILED"
            self._set_current_item_status(record_id, f"{label}: {task.get('title') or f'Recording {record_id}'}")
            self.processed_count += 1
            self._update_file_progress()
        self._finish_queue_mode_if_done()

    def _on_queue_task_skipped(self, task, _reason):
        if task.get("source") != "batch_process":
            return
        first_terminal_event = self._register_batch_terminal_task_once(task)
        if first_terminal_event and self._active_batch_tasks > 0:
            self._active_batch_tasks -= 1
        record_id = task.get("record_id")
        if first_terminal_event and task.get("type") == "transcription" and record_id in self._queued_record_ids:
            self._queued_record_ids.discard(record_id)
            self._set_current_item_status(
                record_id,
                f"SKIPPED: {task.get('title') or f'Recording {record_id}'}",
                background=Qt.GlobalColor.lightGray,
            )
            self.processed_count += 1
            self._update_file_progress()
        self._finish_queue_mode_if_done()
        
    def stop_processing(self):
        self.is_processing = False
        self.status_label.setText("Queued batch is managed by the central queue.")
        self.log("Batch items were queued in the central queue. Use the queue manager to stop them.")

    def retry_failed(self):
        """Reset attempts for selected failed items."""
        selected_items = self.pending_list.selectedItems()
        if not selected_items:
            # If nothing selected, retry ALL failed
            for i in range(self.pending_list.count()):
                item = self.pending_list.item(i)
                rec = item.data(Qt.ItemDataRole.UserRole)
                if rec.get('last_error') or item.background().color() == Qt.GlobalColor.red:
                    self.db.reset_attempts(rec['id'])
        else:
            for item in selected_items:
                rec = item.data(Qt.ItemDataRole.UserRole)
                self.db.reset_attempts(rec['id'])
        
        self.load_pending()
        self.log("Reset attempts for failed items.")

    def cleanup(self):
        self.is_processing = False

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
