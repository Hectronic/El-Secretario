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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QListWidgetItem, QLabel, QSplitter, 
                             QGroupBox, QPushButton, QMessageBox, QApplication, QTextEdit, QProgressDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer, QSettings
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor
from src.database import DBManager
from src.ai_assistant import AIAssistant
from src.summary_generator import SummaryGenerator, get_pending_summary_counts

class CalendarWidget(QWidget):
    """
    Renamed to WeekDetailsWidget internally in spirit. 
    Displays recordings and summaries for the selection mandated by the sidebar calendar.
    """
    start_chat_requested = pyqtSignal(str, list) # Emits (date_str_or_list, tags_list)
    selection_changed = pyqtSignal(QDate, str, str)   # Emits (monday, date_str, tags) to sync back to sidebar

    def __init__(self, rag_engine, task_queue=None, parent=None):
        super().__init__(parent)
        self.rag = rag_engine
        self.summary_task_queue = task_queue
        self.db = DBManager()
        self.selected_recordings = [] # List of dicts
        self.selected_dates = set() # Set of QDate objects
        self.current_week_monday = None # QDate of the Monday of the currently highlighted week
        self.current_anchor_date = None # QDate of the specific day selection or end of range
        
        self.pending_summary_key = None
        self.pending_daily_key = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel: Actions & Tags (Simplified)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.selection_label = QLabel("<b>Selection Context:</b>\nNo context yet")
        self.selection_label.setWordWrap(True)
        left_layout.addWidget(self.selection_label)
        
        # Tag Filter (Keep it so users can refine the view within the tab)
        tag_group = QGroupBox("Filter by Tags")
        tag_layout = QVBoxLayout()
        self.tag_list = QListWidget()
        self.tag_list.itemChanged.connect(self.on_tag_changed)
        tag_layout.addWidget(self.tag_list)
        tag_group.setLayout(tag_layout)
        left_layout.addWidget(tag_group)
        
        # Action Buttons
        self.summary_btn = QPushButton("Generate Weekly Summary")
        self.summary_btn.clicked.connect(self.on_generate_summary_clicked)
        left_layout.addWidget(self.summary_btn)
        
        self.daily_summary_btn = QPushButton("Generate Daily Summary")
        self.daily_summary_btn.clicked.connect(self.on_generate_daily_summary_clicked)
        left_layout.addWidget(self.daily_summary_btn)
        
        self.pending_btn = QPushButton("Generate All Pending")
        self.pending_btn.clicked.connect(self.on_generate_pending_clicked)
        left_layout.addWidget(self.pending_btn)

        splitter.addWidget(left_widget)
        
        # Right Panel: Summaries & Recordings
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Daily Summary
        daily_summary_widget = QWidget()
        daily_summary_layout = QVBoxLayout(daily_summary_widget)
        daily_summary_layout.setContentsMargins(0, 0, 0, 0)
        
        # Day Navigation Buttons
        header_layout = QHBoxLayout()
        self.daily_summary_label = QLabel("<b>Daily Summary:</b>")
        header_layout.addWidget(self.daily_summary_label)
        header_layout.addStretch()
        
        self.prev_day_btn = QPushButton("<")
        self.prev_day_btn.setFixedWidth(30)
        self.prev_day_btn.clicked.connect(self.navigate_prev_day)
        
        self.today_btn = QPushButton("Today")
        self.today_btn.clicked.connect(self.navigate_today)
        
        self.next_day_btn = QPushButton(">")
        self.next_day_btn.setFixedWidth(30)
        self.next_day_btn.clicked.connect(self.navigate_next_day)
        
        header_layout.addWidget(self.prev_day_btn)
        header_layout.addWidget(self.today_btn)
        header_layout.addWidget(self.next_day_btn)
        daily_summary_layout.addLayout(header_layout)
        
        self.daily_summary_text = QTextEdit()
        self.daily_summary_text.setReadOnly(True)
        daily_summary_layout.addWidget(self.daily_summary_text)
        
        # Weekly Summary
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.addWidget(QLabel("<b>Weekly Summary:</b>"))
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_text)
        
        # Recordings List
        recordings_widget = QWidget()
        recordings_layout = QVBoxLayout(recordings_widget)
        recordings_layout.setContentsMargins(0, 0, 0, 0)
        recordings_layout.addWidget(QLabel("<b>Recordings:</b>"))
        self.recording_list = QListWidget()
        recordings_layout.addWidget(self.recording_list)
        
        self.open_tab_btn = QPushButton("Start Chat with Selection")
        self.open_tab_btn.clicked.connect(self.request_new_chat_tab)
        self.open_tab_btn.setMinimumHeight(40)
        recordings_layout.addWidget(self.open_tab_btn)

        right_splitter.addWidget(summary_widget)
        right_splitter.addWidget(daily_summary_widget)
        right_splitter.addWidget(recordings_widget)
        
        splitter.addWidget(right_splitter)
        splitter.setSizes([250, 850])
        right_splitter.setSizes([300, 300, 400])
        
        layout.addWidget(splitter)
        
        self.load_tags()

    def load_tags(self):
        self.tag_list.clear()
        tags = self.db.get_all_tags()
        for tag in tags:
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.tag_list.addItem(item)
            
    def get_selected_tags(self):
        tags = []
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                tags.append(item.text())
        return tags
        
    def on_tag_changed(self, item):
        self.refresh_recordings()
        self.update_daily_summary_view()
        self.update_summary_view()

    def navigate_prev_day(self):
        """Move one day back, maintaining selection mode (progressive or single)."""
        anchor = self.current_anchor_date
        if not anchor:
            if not self.selected_dates: return
            anchor = min(self.selected_dates)
            
        new_date = anchor.addDays(-1)
        
        # Determine if we should maintain progressive mode (if monday was set)
        new_monday = None
        if self.current_week_monday:
            day_of_week = new_date.dayOfWeek()
            new_monday = new_date.addDays(-(day_of_week - 1))
            
        self.set_selection(new_monday, new_date.toString("yyyy-MM-dd"))
        monday_val = self.current_week_monday if self.current_week_monday else QDate()
        self.selection_changed.emit(monday_val, new_date.toString("yyyy-MM-dd"), self.get_tags_filter_str() or "")

    def navigate_today(self):
        """Go to current date."""
        today = QDate.currentDate()
        # Maintain week context if we are in it
        new_monday = None
        if self.current_week_monday:
            day_of_week = today.dayOfWeek()
            new_monday = today.addDays(-(day_of_week - 1))
            
        self.set_selection(new_monday, today.toString("yyyy-MM-dd"))
        monday_val = self.current_week_monday if self.current_week_monday else QDate()
        self.selection_changed.emit(monday_val, today.toString("yyyy-MM-dd"), self.get_tags_filter_str() or "")

    def navigate_next_day(self):
        """Move one day forward, maintaining selection mode (progressive or single)."""
        anchor = self.current_anchor_date
        if not anchor:
            if not self.selected_dates: return
            anchor = max(self.selected_dates)
            
        new_date = anchor.addDays(1)
        
        # Determine if we should maintain progressive mode (if monday was set)
        new_monday = None
        if self.current_week_monday:
            day_of_week = new_date.dayOfWeek()
            new_monday = new_date.addDays(-(day_of_week - 1))
            
        self.set_selection(new_monday, new_date.toString("yyyy-MM-dd"))
        monday_val = self.current_week_monday if self.current_week_monday else QDate()
        self.selection_changed.emit(monday_val, new_date.toString("yyyy-MM-dd"), self.get_tags_filter_str() or "")

    def set_selection(self, monday: QDate, filter_date: str = None, tags_filter: str = None):
        """Called by MainWindow when the sidebar calendar selection changes."""
        self.current_week_monday = monday
        self.selected_dates.clear()
        self.current_anchor_date = None
        
        # Apply tag filter if provided
        if tags_filter is not None:
            self.tag_list.blockSignals(True)
            for i in range(self.tag_list.count()):
                item = self.tag_list.item(i)
                if item.text() == tags_filter:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
            self.tag_list.blockSignals(False)
        elif tags_filter == "": # All
            self.tag_list.blockSignals(True)
            for i in range(self.tag_list.count()):
                self.tag_list.item(i).setCheckState(Qt.CheckState.Unchecked)
            self.tag_list.blockSignals(False)
        
        if filter_date:
            target = QDate.fromString(filter_date, "yyyy-MM-dd")
            self.current_anchor_date = target
            # If we have a monday, we might be in progressive mode
            if monday:
                # Range from monday to filter_date
                curr = monday
                while curr <= target:
                    self.selected_dates.add(curr)
                    curr = curr.addDays(1)
                context = f"Range: {monday.toString('yyyy-MM-dd')} to {filter_date}"
            else:
                # Specific day only
                self.selected_dates.add(target)
                context = f"Day: {filter_date}"
        elif monday:
            # Full week
            for i in range(7):
                self.selected_dates.add(monday.addDays(i))
            self.current_anchor_date = monday.addDays(6) # Default to Sunday
            context = f"Week starting: {monday.toString('yyyy-MM-dd')} (Viewing Sunday)"
        else:
            context = "No selection"

        self.selection_label.setText(f"<b>Selection Context:</b>\n{context}")
        
        self.refresh_recordings()
        self.update_daily_summary_view()
        self.update_summary_view()

    def refresh_recordings(self):
        if not self.selected_dates:
            self.recording_list.clear()
            self.recording_list.addItem("No dates selected.")
            self.selected_recordings = []
            return

        date_strs = sorted([d.toString("yyyy-MM-dd") for d in self.selected_dates])
        tags = self.get_selected_tags()
        self.selected_recordings = self.db.fetch_by_dates(date_strs, tags)
        
        self.recording_list.clear()
        if not self.selected_recordings:
            self.recording_list.addItem("No recordings found.")
        else:
            for rec in self.selected_recordings:
                item_text = f"{rec['created_at']} - {rec['title'] or 'Untitled'}"
                if rec['tags']:
                    item_text += f" [{rec['tags']}]"
                self.recording_list.addItem(item_text)

    def request_new_chat_tab(self):
        if not self.selected_recordings:
            QMessageBox.warning(self, "No Selection", "Please select dates with recordings first.")
            return
            
        date_strs = sorted([d.toString("yyyy-MM-dd") for d in self.selected_dates])
        dates_payload = ",".join(date_strs)
        tags = self.get_selected_tags()
        self.start_chat_requested.emit(dates_payload, tags)

    def get_summary_key(self):
        if not self.current_week_monday:
            return None
        # Use Sunday as the key date
        week_sunday = self.current_week_monday.addDays(6).toString("yyyy-MM-dd")
        tags = tuple(sorted(self.get_selected_tags()))
        return (week_sunday, tags)

    def get_tags_filter_str(self):
        tags = self.get_selected_tags()
        return ",".join(sorted(tags)) if tags else None

    def update_daily_summary_view(self):
        if self.current_anchor_date:
            date = self.current_anchor_date
            date_str = date.toString("yyyy-MM-dd")
            display_date = date.toString("dddd, yyyy-MM-dd")
            tags_filter = self.get_tags_filter_str()
            
            self.daily_summary_label.setText(f"<b>Daily Summary ({display_date.capitalize()}):</b>")
            summary = self.db.get_daily_summary(date_str, tags_filter)
            if summary:
                self.daily_summary_text.setMarkdown(summary)
            else:
                self.daily_summary_text.clear()
                self.daily_summary_text.setPlaceholderText(f"No summary for {date_str}.")
        else:
            self.daily_summary_label.setText("<b>Daily Summary:</b>")
            self.daily_summary_text.clear()
            self.daily_summary_text.setPlaceholderText("Select a single day to view its summary.")

    def update_summary_view(self):
        if not self.current_week_monday:
            self.summary_text.clear()
            return
            
        week_sunday = self.current_week_monday.addDays(6).toString("yyyy-MM-dd")
        tags_filter = self.get_tags_filter_str()
        
        summary = self.db.get_weekly_summary(week_sunday, tags_filter)
        if summary:
            self.summary_text.setMarkdown(summary)
        else:
            self.summary_text.clear()
            self.summary_text.setPlaceholderText("No summary for this week.")

    def on_generate_daily_summary_clicked(self):
        if len(self.selected_dates) != 1:
            QMessageBox.warning(self, "Select One Date", "Please select exactly one date.")
            return
            
        date = list(self.selected_dates)[0]
        date_str = date.toString("yyyy-MM-dd")
        tags = self.get_selected_tags()
        tags_filter = self.get_tags_filter_str()
        
        if self.summary_task_queue:
            self.summary_task_queue.enqueue_daily_summary({
                "date": date_str,
                "tags_filter": tags_filter
            })
            return

        recordings = self.db.fetch_by_dates([date_str], tags)
        if not recordings:
            QMessageBox.warning(self, "No Recordings", "No recordings found.")
            return
            
        full_text = ""
        for rec in recordings:
            full_text += f"\n\n--- Recording: {rec['title'] or 'Untitled'} ({rec['created_at']}) ---\n"
            full_text += rec['transcription'] or ""
            
        if not full_text.strip():
            QMessageBox.warning(self, "No Content", "No transcription content.")
            return
            
        self.progress = QProgressDialog("Generating Daily Summary...", "Cancel", 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.show()
        
        settings = QSettings("Hectronic", "Secretario")
        from src.ai_provider import validate_ai_provider_config
        is_valid, error_msg = validate_ai_provider_config(settings)
        if not is_valid:
            self.progress.close()
            QMessageBox.critical(self, "Error", error_msg)
            return
            
        self.pending_daily_key = (date_str, self.get_tags_filter_str())
        self.worker = AIAssistant("", "daily_summary", full_text)
        self.worker.task_completed.connect(self.on_summary_finished)
        self.worker.error.connect(self.on_summary_error)
        self.worker.start()

    def on_generate_summary_clicked(self):
        if not self.current_week_monday:
            QMessageBox.warning(self, "No Week Selected", "No week context.")
            return
            
        week_sunday = self.current_week_monday.addDays(6).toString("yyyy-MM-dd")
        week_dates = [self.current_week_monday.addDays(i).toString("yyyy-MM-dd") for i in range(7)]
        tags = self.get_selected_tags()
        recordings_for_summary = self.db.fetch_by_dates(week_dates, tags)
        
        if not recordings_for_summary:
            QMessageBox.warning(self, "No Recordings", "No recordings found for the week.")
            return

        full_text = ""
        for rec in recordings_for_summary:
            full_text += f"\n\n--- Recording: {rec['title'] or 'Untitled'} ({rec['created_at']}) ---\n"
            full_text += rec['transcription'] or ""

        if not full_text.strip():
            QMessageBox.warning(self, "No Content", "No transcription content.")
            return

        if self.summary_task_queue:
            tags_filter = self.get_tags_filter_str() or ""
            self.summary_task_queue.enqueue_weekly_summary(week_sunday, full_text, tags_filter)
            return

        self.progress = QProgressDialog("Generating Weekly Summary...", "Cancel", 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.show()

        settings = QSettings("Hectronic", "Secretario")
        from src.ai_provider import validate_ai_provider_config
        is_valid, error_msg = validate_ai_provider_config(settings)
        if not is_valid:
            self.progress.close()
            QMessageBox.critical(self, "Error", error_msg)
            return

        self.pending_summary_key = self.get_summary_key()
        self.worker = AIAssistant("", "weekly_summary", full_text)
        self.worker.task_completed.connect(self.on_summary_finished)
        self.worker.error.connect(self.on_summary_error)
        self.worker.start()

    def on_generate_pending_clicked(self):
        tags_filter = self.get_tags_filter_str()
        pending_daily, pending_weekly = get_pending_summary_counts(tags_filter)
        
        if pending_daily == 0 and pending_weekly == 0:
            QMessageBox.information(self, "All Done", "No pending summaries.")
            return
            
        msg = f"Found {pending_daily} days and {pending_weekly} weeks without summaries.\n\nGenerate all?"
        reply = QMessageBox.question(self, "Generate Pending", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.pending_progress = QProgressDialog("Generating pending summaries...", "Cancel", 0, pending_daily + pending_weekly, self)
        self.pending_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.pending_progress.show()
        
        self.summary_generator = SummaryGenerator(True, True, tags_filter, parent=self)
        self.summary_generator.progress.connect(self.on_pending_progress)
        self.summary_generator.finished.connect(self.on_pending_finished)
        self.summary_generator.error.connect(self.on_pending_error)
        self.pending_progress.canceled.connect(self.summary_generator.cancel)
        self.summary_generator.start()

    def on_pending_progress(self, current, total):
        if hasattr(self, 'pending_progress'):
            self.pending_progress.setValue(current)

    def on_pending_finished(self, daily_count, weekly_count):
        if hasattr(self, 'pending_progress'):
            self.pending_progress.close()
        QMessageBox.information(self, "Complete", f"Generated {daily_count} daily and {weekly_count} weekly summaries.")
        self.update_daily_summary_view()
        self.update_summary_view()

    def on_pending_error(self, error_msg):
        if hasattr(self, 'pending_progress'):
            self.pending_progress.close()
        QMessageBox.critical(self, "Error", f"Failed: {error_msg}")

    def on_summary_finished(self, task_type, result):
        if hasattr(self, 'progress'):
            self.progress.close()
        
        if task_type == "weekly_summary":
            if self.pending_summary_key:
                week_str, tags_tuple = self.pending_summary_key
                tags_filter = ",".join(tags_tuple) if tags_tuple else None
                self.db.save_weekly_summary(week_str, result, tags_filter)
                if self.pending_summary_key == self.get_summary_key():
                    self.update_summary_view()
            self.pending_summary_key = None
            
        elif task_type == "daily_summary":
            if self.pending_daily_key:
                date_str, tags_filter = self.pending_daily_key
                self.db.save_daily_summary(date_str, result, tags_filter)
                if len(self.selected_dates) == 1:
                    current_date = list(self.selected_dates)[0].toString("yyyy-MM-dd")
                    if current_date == date_str:
                        self.update_daily_summary_view()
            self.pending_daily_key = None

    def on_summary_error(self, error_msg):
        if hasattr(self, 'progress'):
            self.progress.close()
        self.pending_summary_key = None
        self.pending_daily_key = None
        QMessageBox.critical(self, "Error", f"Failed: {error_msg}")
