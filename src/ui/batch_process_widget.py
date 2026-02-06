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
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from src.database import DBManager
from src.worker import TranscriberThread
from PyQt6.QtCore import QSettings

class BatchProcessWidget(QWidget):
    finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DBManager()
        self.queue = []
        self.current_thread = None
        self.is_processing = False
        self.total_files = 0
        self.processed_count = 0
        
        self.init_ui()
        self.load_pending()
        
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
        self.file_progress_label.setText(f"0/{self.total_files} files processed")
        self.log(f"Found {self.total_files} pending recordings.")
        
        self.pending_list.clear()
        for rec in self.queue:
            item = QListWidgetItem(f"{rec['filename']} ({rec['duration']:.1f}s)")
            item.setData(Qt.ItemDataRole.UserRole, rec)
            
            # Highlight errors
            if rec.get('last_error'):
                item.setText(f"FAILED: {rec['filename']} (Attempts: {rec.get('processing_attempts')})")
                item.setBackground(Qt.GlobalColor.red)
                item.setForeground(Qt.GlobalColor.white)
                item.setToolTip(rec['last_error'])
                
            self.pending_list.addItem(item)
        
        if self.total_files == 0:
            self.start_btn.setEnabled(False)
            self.status_label.setText("No pending recordings found.")
        else:
            self.start_btn.setEnabled(True)
            self.status_label.setText("Ready to start.")

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
        if not self.queue:
            return
            
        self.is_processing = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.processed_count = 0
        self.process_next()
        
    def stop_processing(self):
        self.is_processing = False
        self.status_label.setText("Stopping after current file...")
        self.log("Stopping requested...")
        # We can't easily kill the thread safely, so we just stop the queue.
        # If we wanted to kill it, we'd need to add a stop flag to the thread.
        
    def process_next(self):
        if not self.is_processing or not self.queue:
            self.finish_processing()
            return
            
        # Peek at the next item, don't pop it yet until we know it's processed or failed
        # Actually, we need to pop it from the queue to advance, but we keep it in the list
        # until success.
        
        record = self.queue[0]
        self.current_record = record
        
        # Find the item in the list
        self.current_item = None
        for i in range(self.pending_list.count()):
            item = self.pending_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole)['id'] == record['id']:
                self.current_item = item
                break
        
        if self.current_item:
            self.current_item.setText(f"Processing: {record['filename']}...")
            self.current_item.setBackground(Qt.GlobalColor.yellow)

        filename = record['filename']
        file_path = os.path.join(os.getcwd(), "recordings", filename)
        
        if not os.path.exists(file_path):
            self.log(f"File not found: {filename}. Skipping.")
            self.on_file_error(f"File not found: {file_path}")
            return
            
        self.status_label.setText(f"Processing: {filename}")
        self.log(f"Starting: {filename}")
        self.progress_bar.setValue(0)
        
        settings = QSettings("Hectronic", "Secretario")
        hf_token = settings.value("hf_token", "")
        force_cpu = settings.value("force_cpu", False, type=bool)
        compute_type = settings.value("compute_type", "int8")
        if compute_type == "auto":
            compute_type = None
        
        # Use large-v3 and enable diarization as requested
        self.thread = TranscriberThread(
            file_path, 
            model_size="large-v3", 
            compute_type=compute_type,
            hf_token=hf_token, 
            enable_diarization=True,
            total_duration=record['duration'],
            force_cpu=force_cpu
        )
        
        self.thread.finished.connect(self.on_file_finished)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.status_update.connect(lambda s: self.status_label.setText(f"{filename}: {s}"))
        self.thread.error.connect(self.on_file_error)
        self.thread.start()
        

        
    def cleanup_thread(self):
        if self.thread:
            try:
                self.thread.wait()
                self.thread.deleteLater()
            except:
                pass
            self.thread = None
            
    def on_file_finished(self, result):
        self.cleanup_thread() # Cleanup previous thread
        if not self.is_processing:
            return

        record_id = self.current_record['id']
        text = result["text"]
        
        # Update DB
        self.db.update_transcription(
            record_id, 
            text, 
            is_diarized=result.get("is_diarized", False), 
            transcription_model=result.get("model_name")
        )
        
        # Log transcription event
        self.db.log_transcription(
            model_name=result["model_name"],
            audio_duration=result["audio_duration"],
            audio_size_bytes=result["audio_size_bytes"],
            transcription_time_seconds=result["transcription_time"],
            record_id=record_id
        )
        
        self.log(f"Finished: {self.current_record['filename']}")
        self.processed_count += 1
        self.file_progress_label.setText(f"{self.processed_count}/{self.total_files} files processed")
        
        # Remove from queue and list on success
        if self.queue:
            self.queue.pop(0)
            
        if self.current_item:
            row = self.pending_list.row(self.current_item)
            self.pending_list.takeItem(row)
        
        self.process_next()
        
    def on_file_error(self, err):
        self.cleanup_thread() # Cleanup previous thread
        error_msg = str(err)
        self.log(f"Error processing {self.current_record['filename']}: {error_msg}")
        
        record_id = self.current_record['id']
        
        # Save error to DB
        self.db.set_error(record_id, error_msg)
        attempts = self.db.increment_attempt(record_id)
        
        # Update item in list to show error
        if self.current_item:
            self.current_item.setText(f"FAILED: {self.current_record['filename']} (Attempts: {attempts})")
            self.current_item.setBackground(Qt.GlobalColor.red)
            self.current_item.setForeground(Qt.GlobalColor.white)
            self.current_item.setToolTip(error_msg)
            
        # Retry logic
        if attempts < 3:
            self.log(f"Retrying... (Attempt {attempts + 1}/3)")
            self.status_label.setText(f"Retrying {self.current_record['filename']}...")
            # We don't pop from queue, so it will be retried in next process_next call
            # But we need to delay slightly? Loop handled via signal, so safe to call process_next
            # Maybe add a small delay?
            QTimer.singleShot(2000, self.process_next)
            return

        self.log("Max retries reached. Moving to next file.")

        # Remove from queue so we move to next, but KEEP in list
        if self.queue:
            self.queue.pop(0)
            
        # Continue to next even on error
        self.process_next()

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
        
    def finish_processing(self):
        self.is_processing = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Batch processing finished.")
        self.progress_bar.setValue(100)
        self.log("All done.")
        QMessageBox.information(self, "Done", "Batch processing completed.")
