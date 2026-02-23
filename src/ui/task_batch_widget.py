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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QProgressBar, QTextEdit, QMessageBox, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from src.database import DBManager

class TaskBatchWidget(QWidget):
    """
    Widget for batch extracting tasks from recordings that are missing them.
    """
    
    def __init__(self, task_queue=None, parent=None):
        super().__init__(parent)
        self.db = DBManager()
        self.task_queue = task_queue
        self.is_processing = False
        self.pending_records = []
        
        self.init_ui()
        self.refresh_stats()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Batch Task Extraction")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #009688;")
        layout.addWidget(header)
        
        description = QLabel(
            "Extract actionable tasks from previous recordings that don't have them yet. "
            "This will use the AI to identify to-do items and save them to the database."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Stats Label
        self.stats_label = QLabel("Checking for recordings without tasks...")
        self.stats_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.stats_label)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Log Area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Operation log will appear here...")
        layout.addWidget(self.log_text)
        
        # Controls
        btn_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Stats")
        self.refresh_btn.clicked.connect(self.refresh_stats)
        btn_layout.addWidget(self.refresh_btn)
        
        self.start_btn = QPushButton("Start Extraction")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setStyleSheet("background-color: #009688; color: white; font-weight: bold; padding: 10px;")
        btn_layout.addWidget(self.start_btn)
        
        layout.addLayout(btn_layout)

    def log(self, message):
        self.log_text.append(message)
        
    def refresh_stats(self):
        """Query DB for recordings without tasks."""
        self.pending_records = self.db.get_records_without_tasks()
        count = len(self.pending_records)
        self.stats_label.setText(f"Found {count} recordings without tasks.")
        
        if count == 0:
            self.start_btn.setEnabled(False)
            self.start_btn.setText("All tasks extracted")
        else:
            self.start_btn.setEnabled(True)
            self.start_btn.setText(f"Extract Tasks from {count} recordings")
            
    def start_processing(self):
        if not self.task_queue:
            QMessageBox.warning(self, "Error", "Task Queue not available.")
            return
            
        if not self.pending_records:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Batch Action",
            f"This will enqueue {len(self.pending_records)} task extraction jobs. "
            "They will be processed sequentially in the background.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.log(f"Enqueuing {len(self.pending_records)} tasks...")
        
        count = 0
        for rec in self.pending_records:
            # enqueue_task_extraction(self, record_id: int, text: str, tags: str)
            success = self.task_queue.enqueue_task_extraction(
                rec['id'], 
                rec.get('transcription', ''), 
                rec.get('tags', '') or '',
                rec.get('title') or f"Recording {rec['id']}"
            )
            if success:
                count += 1
                
        self.log(f"Successfully enqueued {count} extraction jobs.")
        QMessageBox.information(self, "Tasks Enqueued", f"{count} task extraction jobs have been added to the queue.")
        
        self.refresh_stats()
