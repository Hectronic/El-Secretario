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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QProgressBar, QTextEdit, QMessageBox, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from src.database import DBManager
from src.summary_generator import SummaryGenerator

class SummaryBatchWidget(QWidget):
    """
    Widget for batch generating summaries for pending days, weeks, and recordings.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DBManager()
        self.generator = None
        self.is_processing = False
        
        self.init_ui()
        self.refresh_stats()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Batch Summary Generation")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #3F51B5;")
        layout.addWidget(header)
        
        description = QLabel(
            "Automatically generate summaries for past days, weeks, and individual recordings "
            "that are missing them. You can exclude today and the current week."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Options Group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        # Checkboxes
        self.chk_recordings = QCheckBox("Generate Missing Recording Summaries")
        self.chk_recordings.setChecked(True)
        self.chk_recordings.stateChanged.connect(self.refresh_stats_display)
        options_layout.addWidget(self.chk_recordings)
        
        self.chk_daily = QCheckBox("Generate Missing Daily Summaries")
        self.chk_daily.setChecked(True)
        self.chk_daily.stateChanged.connect(self.refresh_stats_display)
        options_layout.addWidget(self.chk_daily)
        
        self.chk_weekly = QCheckBox("Generate Missing Weekly Summaries")
        self.chk_weekly.setChecked(True)
        self.chk_weekly.stateChanged.connect(self.refresh_stats_display)
        options_layout.addWidget(self.chk_weekly)
        
        # Exclusions
        self.chk_exclude_today = QCheckBox("Exclude Today (Daily)")
        self.chk_exclude_today.setChecked(True)
        self.chk_exclude_today.setToolTip("Don't generate summary for today as it might be incomplete.")
        self.chk_exclude_today.stateChanged.connect(self.refresh_stats) # Need to requery DB
        options_layout.addWidget(self.chk_exclude_today)
        
        self.chk_exclude_curr_week = QCheckBox("Exclude Current Week (Weekly)")
        self.chk_exclude_curr_week.setChecked(True)
        self.chk_exclude_curr_week.setToolTip("Don't generate summary for current week as it is incomplete.")
        self.chk_exclude_curr_week.stateChanged.connect(self.refresh_stats) # Need to requery DB
        options_layout.addWidget(self.chk_exclude_curr_week)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Stats Label
        self.stats_label = QLabel("Loading stats...")
        self.stats_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(self.stats_label)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)
        
        # Log Area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # Controls
        btn_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refresh Stats")
        self.refresh_btn.clicked.connect(self.refresh_stats)
        btn_layout.addWidget(self.refresh_btn)
        
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
        
        # Store counts
        self.pending_rec_count = 0
        self.pending_day_count = 0
        self.pending_week_count = 0
        
    def refresh_stats(self):
        """Query DB for pending counts based on current exclusion settings."""
        if self.is_processing:
            return
            
        exclude_today = self.chk_exclude_today.isChecked()
        exclude_curr_week = self.chk_exclude_curr_week.isChecked()
        
        # TODO: Thread this if it becomes slow
        recs = self.db.get_records_without_summary()
        dates = self.db.get_dates_without_summary(exclude_today=exclude_today)
        weeks = self.db.get_weeks_without_summary(exclude_current_week=exclude_curr_week)
        
        self.pending_rec_count = len(recs)
        self.pending_day_count = len(dates)
        self.pending_week_count = len(weeks)
        
        self.refresh_stats_display()
        self.log("Stats refreshed.")
        
    def refresh_stats_display(self):
        """Update stats label based on checkboxes."""
        txt = "Found:\n"
        total_selected = 0
        
        rec_txt = f"- {self.pending_rec_count} recordings without summary"
        if self.chk_recordings.isChecked():
            rec_txt = f"<b>{rec_txt}</b> (Selected)"
            total_selected += self.pending_rec_count
        txt += rec_txt + "\n"
        
        day_txt = f"- {self.pending_day_count} days without summary"
        if self.chk_daily.isChecked():
            day_txt = f"<b>{day_txt}</b> (Selected)"
            total_selected += self.pending_day_count
        txt += day_txt + "\n"
        
        week_txt = f"- {self.pending_week_count} weeks without summary"
        if self.chk_weekly.isChecked():
            week_txt = f"<b>{week_txt}</b> (Selected)"
            total_selected += self.pending_week_count
        txt += week_txt + "\n"
        
        self.stats_label.setText(txt)
        
        if total_selected == 0:
            self.start_btn.setEnabled(False)
            self.start_btn.setText("Nothing Selected")
        else:
            self.start_btn.setEnabled(True)
            self.start_btn.setText(f"Start Processing ({total_selected} items)")

    def log(self, message):
        self.log_text.append(message)
        
    def start_processing(self):
        if self.is_processing:
            return
            
        self.is_processing = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.refresh_btn.setEnabled(False)
        self.chk_recordings.setEnabled(False)
        self.chk_daily.setEnabled(False)
        self.chk_weekly.setEnabled(False)
        self.chk_exclude_today.setEnabled(False)
        self.chk_exclude_curr_week.setEnabled(False)
        
        self.log("Starting batch processing...")
        self.progress_bar.setValue(0)
        
        self.generator = SummaryGenerator(
            generate_daily=self.chk_daily.isChecked(),
            generate_weekly=self.chk_weekly.isChecked(),
            generate_recordings=self.chk_recordings.isChecked(),
            exclude_today=self.chk_exclude_today.isChecked(),
            exclude_current_week=self.chk_exclude_curr_week.isChecked()
        )
        
        self.generator.progress.connect(self.on_progress)
        self.generator.item_completed.connect(self.on_item_completed)
        self.generator.finished.connect(self.on_finished)
        self.generator.error.connect(self.on_error)
        
        self.generator.start()
        
    def stop_processing(self):
        if self.generator and self.is_processing:
            self.log("Stopping requested...")
            self.generator.cancel()
            self.stop_btn.setEnabled(False) # Prevent double click
            
    def on_progress(self, current, total):
        self.progress_bar.setValue(int((current / total) * 100))
        self.progress_label.setText(f"Processing item {current} of {total}...")
        
    def on_item_completed(self, type_, identifier, summary):
        short_summary = (summary[:50] + '...') if len(summary) > 50 else summary
        short_summary = short_summary.replace("\n", " ")
        
        if type_ == "recording":
            self.log(f"✓ Generated summary for recording: {identifier}")
        elif type_ == "daily":
            self.log(f"✓ Generated summary for day: {identifier}")
        elif type_ == "weekly":
            self.log(f"✓ Generated summary for week starting: {identifier}")
            
    def on_finished(self, rec_count, daily_count, weekly_count):
        self.log(f"Batch processing complete.")
        self.log(f"Processed: {rec_count} recordings, {daily_count} days, {weekly_count} weeks.")
        QMessageBox.information(
            self, "Complete",
            f"Batch processing finished!\n\n"
            f"Recordings: {rec_count}\n"
            f"Days: {daily_count}\n"
            f"Weeks: {weekly_count}"
        )
        self.reset_ui()
        self.refresh_stats()
        
    def on_error(self, error_msg):
        self.log(f"ERROR: {error_msg}")
        QMessageBox.critical(self, "Error", f"Processing failed: {error_msg}")
        self.reset_ui()
        self.refresh_stats()
        
    def reset_ui(self):
        self.is_processing = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.refresh_btn.setEnabled(True)
        self.chk_recordings.setEnabled(True)
        self.chk_daily.setEnabled(True)
        self.chk_weekly.setEnabled(True)
        self.chk_exclude_today.setEnabled(True)
        self.chk_exclude_curr_week.setEnabled(True)
