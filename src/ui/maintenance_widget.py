# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QProgressBar, QHBoxLayout, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QTimer
import os


class MaintenanceWidget(QWidget):
    """Widget for storage cleanup and statistics."""

    def __init__(self, db, notebook_db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.notebook_db = notebook_db
        
        self.init_ui()
        self.calculate_stats()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Align to top for tab view
        layout.setContentsMargins(40, 40, 40, 40) # Add margins

        # Title
        title = QLabel("System Maintenance")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #607D8B;")
        layout.addWidget(title)

        # Stats Section
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #444;
                border-radius: 5px;
                background-color: #2b2b2b;
            }
            QLabel {
                border: none;
                color: #eee;
                font-size: 16px;
                padding: 5px;
            }
        """)
        stats_layout = QVBoxLayout(stats_frame)
        
        self.total_lbl = QLabel("Total Recordings: -")
        stats_layout.addWidget(self.total_lbl)
        
        self.diarized_lbl = QLabel("Diarized Recordings: -")
        stats_layout.addWidget(self.diarized_lbl)
        
        self.pending_lbl = QLabel("Pending Diarization: -")
        stats_layout.addWidget(self.pending_lbl)
        
        self.space_lbl = QLabel("Reclaimable Space: -")
        self.space_lbl.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 16px; padding: 5px;")
        stats_layout.addWidget(self.space_lbl)
        
        layout.addWidget(stats_frame)

        # Info Text
        info = QLabel("You can delete audio files for recordings that have already been diarized (processed). The text and metadata will be preserved, but you won't be able to listen to the audio anymore.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #aaa; font-size: 14px;")
        layout.addWidget(info)

        # Progress Bar
        self.progressBar = QProgressBar()
        self.progressBar.hide()
        layout.addWidget(self.progressBar)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.clean_btn = QPushButton("Clean Up Audio Files")
        self.clean_btn.setFixedSize(200, 50)
        self.clean_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 15px;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.clean_btn.clicked.connect(self.clean_up)
        btn_layout.addWidget(self.clean_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        layout.addStretch() # Push everything up

    def calculate_stats(self):
        records = self.db.fetch_all()
        diarized_records = self.db.fetch_diarized_records()
        pending_records = self.db.fetch_pending_diarization()
        
        total_count = len(records)
        diarized_count = len(diarized_records)
        pending_count = len(pending_records)
        
        total_size = 0
        self.reclaimable_files = []
        
        recordings_dir = os.path.join(os.getcwd(), "recordings")
        
        for record in diarized_records:
            filename = record['filename']
            filepath = os.path.join(recordings_dir, filename)
            if os.path.exists(filepath):
                try:
                    size = os.path.getsize(filepath)
                    total_size += size
                    self.reclaimable_files.append(filepath)
                except:
                    pass
        
        # Format size
        size_mb = total_size / (1024 * 1024)
        if size_mb > 1024:
            size_str = f"{size_mb/1024:.2f} GB"
        else:
            size_str = f"{size_mb:.2f} MB"
            
        self.total_lbl.setText(f"Total Recordings: {total_count}")
        self.diarized_lbl.setText(f"Diarized Recordings: {diarized_count}")
        self.pending_lbl.setText(f"Pending Diarization: {pending_count}")
        self.space_lbl.setText(f"Reclaimable Space: {size_str}")
        
        if not self.reclaimable_files:
            self.clean_btn.setEnabled(False)
            self.clean_btn.setText("Nothing to clean")
        else:
            self.clean_btn.setEnabled(True)
            self.clean_btn.setText("Clean Up Audio Files")

    def clean_up(self):
        count = len(self.reclaimable_files)
        if count == 0:
            return

        reply = QMessageBox.question(self, "Confirm Cleanup", 
                                   f"Are you sure you want to delete {count} audio files? This action cannot be undone.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.clean_btn.setEnabled(False)
            self.progressBar.setMaximum(count)
            self.progressBar.setValue(0)
            self.progressBar.show()
            
            self.files_to_delete = list(self.reclaimable_files)
            self.deleted_count = 0
            QTimer.singleShot(10, self.process_next_file)

    def process_next_file(self):
        if not self.files_to_delete:
            self.finish_cleanup()
            return
            
        filepath = self.files_to_delete.pop(0)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Error deleting {filepath}: {e}")
            
        self.deleted_count += 1
        self.progressBar.setValue(self.deleted_count)
        
        QTimer.singleShot(5, self.process_next_file)
        
    def finish_cleanup(self):
        QMessageBox.information(self, "Cleanup Complete", f"Successfully deleted {self.deleted_count} files.")
        self.progressBar.hide()
        self.calculate_stats() # Recalculate
