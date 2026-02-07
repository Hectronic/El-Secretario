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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget, 
                             QListWidget, QListWidgetItem, QLabel, QSplitter, 
                             QCheckBox, QGroupBox, QPushButton, QMessageBox, QApplication, QTextEdit, QProgressDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer, QSettings
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor
from src.database import DBManager
from src.ai_assistant import AIAssistant
from src.summary_generator import SummaryGenerator, get_pending_summary_counts

class CalendarWidget(QWidget):
    start_chat_requested = pyqtSignal(str, list) # Emits (date_str_or_list, tags_list)

    def __init__(self, rag_engine, parent=None):
        super().__init__(parent)
        self.rag = rag_engine
        self.db = DBManager()
        self.selected_recordings = [] # List of dicts
        self.selected_dates = set() # Set of QDate objects
        self.current_week_monday = None # QDate of the Monday of the currently highlighted week
        self.last_clicked_date = None
        
        self.pending_summary_key = None
        self.pending_daily_key = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel: Filters
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Calendar
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        # self.calendar.setSelectionMode(QCalendarWidget.SelectionMode.NoSelection) # Removed to avoid interaction issues
        self.calendar.clicked.connect(self.on_date_clicked)
        left_layout.addWidget(self.calendar)
        
        # Tag Filter
        tag_group = QGroupBox("Filter by Tags")
        tag_layout = QVBoxLayout()
        self.tag_list = QListWidget()
        self.tag_list.itemChanged.connect(self.on_tag_changed)
        tag_layout.addWidget(self.tag_list)
        tag_group.setLayout(tag_layout)
        left_layout.addWidget(tag_group)
        
        # Refresh Tags Button
        refresh_btn = QPushButton("Refresh Tags")
        refresh_btn.clicked.connect(self.load_tags)
        left_layout.addWidget(refresh_btn)
        
        # Week Navigation
        nav_layout = QHBoxLayout()
        self.prev_week_btn = QPushButton("<< Prev Week")
        self.prev_week_btn.clicked.connect(self.on_prev_week_clicked)
        self.next_week_btn = QPushButton("Next Week >>")
        self.next_week_btn.clicked.connect(self.on_next_week_clicked)
        nav_layout.addWidget(self.prev_week_btn)
        nav_layout.addWidget(self.next_week_btn)
        left_layout.addLayout(nav_layout)

        # Generate Summary Buttons
        self.summary_btn = QPushButton("Generate Weekly Summary")
        self.summary_btn.clicked.connect(self.on_generate_summary_clicked)
        left_layout.addWidget(self.summary_btn)
        
        self.daily_summary_btn = QPushButton("Generate Daily Summary")
        self.daily_summary_btn.clicked.connect(self.on_generate_daily_summary_clicked)
        left_layout.addWidget(self.daily_summary_btn)
        
        # Generate Pending Summaries Button
        self.pending_btn = QPushButton("Generate All Pending Summaries")
        self.pending_btn.clicked.connect(self.on_generate_pending_clicked)
        left_layout.addWidget(self.pending_btn)

        splitter.addWidget(left_widget)
        
        # Right Panel: Recordings + Summary (Vertical Splitter)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top: Recordings List
        recordings_widget = QWidget()
        recordings_layout = QVBoxLayout(recordings_widget)
        recordings_layout.setContentsMargins(0, 0, 0, 0)
        recordings_layout.addWidget(QLabel("<b>Recordings for Selection:</b>"))
        
        self.recording_list = QListWidget()
        recordings_layout.addWidget(self.recording_list)
        
        # Open in New Tab Button
        self.open_tab_btn = QPushButton("Start Chat with Selection")
        self.open_tab_btn.clicked.connect(self.request_new_chat_tab)
        self.open_tab_btn.setMinimumHeight(40)
        recordings_layout.addWidget(self.open_tab_btn)
        
        right_splitter.addWidget(recordings_widget)
        
        # Middle: Daily Summary
        daily_summary_widget = QWidget()
        daily_summary_layout = QVBoxLayout(daily_summary_widget)
        daily_summary_layout.setContentsMargins(0, 0, 0, 0)
        daily_summary_layout.addWidget(QLabel("<b>Daily Summary:</b>"))
        
        self.daily_summary_text = QTextEdit()
        self.daily_summary_text.setReadOnly(True)
        daily_summary_layout.addWidget(self.daily_summary_text)
        
        right_splitter.addWidget(daily_summary_widget)
        
        # Bottom: Weekly Summary
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.addWidget(QLabel("<b>Weekly Summary:</b>"))
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_text)
        
        right_splitter.addWidget(summary_widget)
        
        # Add to main splitter
        splitter.addWidget(right_splitter)
        
        # Set initial sizes
        splitter.setSizes([300, 800])
        right_splitter.setSizes([300, 200, 300])
        
        layout.addWidget(splitter)
        
        # Initial Load
        self.load_tags()
        # Select today by default
        today = QDate.currentDate()
        self.selected_dates.add(today)
        self.last_clicked_date = today
        
        # Set current week
        day_of_week = today.dayOfWeek()
        self.current_week_monday = today.addDays(-(day_of_week - 1))
        
        # Defer highlight
        QTimer.singleShot(100, self.highlight_dates)
        self.refresh_recordings()
        
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
        
    def on_date_clicked(self, date):
        print(f"DEBUG: Date clicked: {date.toString()}")
        try:
            previous_selection = self.selected_dates.copy()
            previous_week_monday = self.current_week_monday
            
            modifiers = QApplication.keyboardModifiers()
            
            # Update current week based on clicked date
            day_of_week = date.dayOfWeek()
            self.current_week_monday = date.addDays(-(day_of_week - 1))
            
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                # Toggle selection
                if date in self.selected_dates:
                    self.selected_dates.remove(date)
                else:
                    self.selected_dates.add(date)
                self.last_clicked_date = date
                
            elif modifiers & Qt.KeyboardModifier.ShiftModifier and self.last_clicked_date:
                # Range selection
                start = min(self.last_clicked_date, date)
                end = max(self.last_clicked_date, date)
                
                curr = start
                while curr <= end:
                    self.selected_dates.add(curr)
                    curr = curr.addDays(1)
                    
                # For multi-selection, update week to the latest date's week
                # (Already done above since date is the clicked date)
                    
            else:
                # Single selection -> Select ONLY that date
                self.selected_dates.clear()
                self.selected_dates.add(date)
                self.last_clicked_date = date
                
            # Update visuals
            # We need to refresh if selection changed OR if week changed
            if previous_selection != self.selected_dates or previous_week_monday != self.current_week_monday:
                self.update_calendar_visuals(previous_selection, previous_week_monday)
                self.update_daily_summary_view()
                if previous_week_monday != self.current_week_monday:
                    self.update_summary_view()
                
            self.refresh_recordings()
        except Exception as e:
            print(f"ERROR in on_date_clicked: {e}")
            import traceback
            traceback.print_exc()
        
    def update_calendar_visuals(self, previous_selection, previous_week_monday=None):
        # Format for Selected Dates (Dark Blue)
        selected_fmt = QTextCharFormat()
        selected_fmt.setBackground(QColor("#2196F3"))
        selected_fmt.setForeground(QColor("white"))
        
        # Format for Week Context (Light Blue/Gray)
        week_fmt = QTextCharFormat()
        week_fmt.setBackground(QColor("#E3F2FD")) # Light Blue
        # week_fmt.setForeground(QColor("black")) # Keep default text color?
        
        normal_fmt = QTextCharFormat()
        normal_fmt.setBackground(Qt.GlobalColor.transparent)
        normal_fmt.setForeground(QColor("#e0e0e0")) 
        
        # Clear previous week highlight if it changed
        if previous_week_monday and previous_week_monday != self.current_week_monday:
            for i in range(7):
                day = previous_week_monday.addDays(i)
                # Only clear if not in current selection (will be handled below)
                # But simpler to just clear everything and re-apply
                self.calendar.setDateTextFormat(day, normal_fmt)

        # Clear previous selection
        for date in previous_selection:
             self.calendar.setDateTextFormat(date, normal_fmt)

        # Apply Week Highlight
        if self.current_week_monday:
            for i in range(7):
                day = self.current_week_monday.addDays(i)
                self.calendar.setDateTextFormat(day, week_fmt)

        # Apply Selection (Overwrites Week Highlight)
        for date in self.selected_dates:
            self.calendar.setDateTextFormat(date, selected_fmt)

    def highlight_dates(self):
        # Initial highlight helper
        self.update_calendar_visuals(set())

    def refresh_recordings(self):
        if not self.selected_dates:
            self.recording_list.clear()
            self.recording_list.addItem("No dates selected.")
            self.selected_recordings = []
            return

        date_strs = [d.toString("yyyy-MM-dd") for d in self.selected_dates]
        tags = self.get_selected_tags()
        
        self.selected_recordings = self.db.fetch_by_dates(date_strs, tags)
        
        self.recording_list.clear()
        if not self.selected_recordings:
            self.recording_list.addItem("No recordings found for selected dates.")
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
            
        # Pass list of date strings
        date_strs = [d.toString("yyyy-MM-dd") for d in self.selected_dates]
        # Sort them for consistency
        date_strs.sort()
        
        # If it's a single date, pass as string for backward compatibility if needed, 
        # but signal signature says list? No, signal signature was str, list.
        # I updated signal to be flexible or just change it.
        # Let's change signal to emit a string representation of the range AND the list of dates?
        # Or just emit the list and let the receiver handle it.
        # The receiver (MainWindow) expects (date_str, tags).
        # I should probably update the signal to be (str, list) where str is a display name.
        
        # Construct a display name for the date range
        if len(date_strs) == 1:
            date_display = date_strs[0]
        else:
            date_display = f"{len(date_strs)} days selected"
            
        tags = self.get_selected_tags()
        
        # We need to pass the actual dates to the chat so it can filter.
        # The current chat implementation filters by a single date string or "All".
        # We need to update ChatWidget/DBManager to handle multiple dates if we want that.
        # BUT, the user asked for "sequences of days or even loose days".
        # So we definitely need to support a list of dates in the filter.
        
        # For now, let's serialize the dates into a JSON string or special format if we can't change the signature easily?
        # Or better, just pass the list.
        # I will emit (date_display, tags) but I need to pass the dates somehow.
        # Wait, the signal is `start_chat_requested`.
        # In MainWindow: `self.calendar_widget.start_chat_requested.connect(self.open_chat_tab_from_calendar)`
        # `open_chat_tab_from_calendar(self, date_str, tags)`
        # It uses `date_str` as `filter_date`.
        # `DBManager.fetch_chat_sessions` and `save_chat_session` use `filter_date` as TEXT.
        # So I can store a JSON list of dates in `filter_date` column?
        # Or a comma-separated string.
        
        dates_payload = ",".join(date_strs)
        self.start_chat_requested.emit(dates_payload, tags)

    def on_prev_week_clicked(self):
        if not self.current_week_monday:
            today = QDate.currentDate()
            self.current_week_monday = today.addDays(-(today.dayOfWeek() - 1))
            
        previous_week = self.current_week_monday
        self.current_week_monday = self.current_week_monday.addDays(-7)
        
        # Update calendar page to show the new week
        self.calendar.setCurrentPage(self.current_week_monday.year(), self.current_week_monday.month())
        
        self.update_calendar_visuals(self.selected_dates, previous_week)
        self.update_summary_view()

    def on_next_week_clicked(self):
        if not self.current_week_monday:
            today = QDate.currentDate()
            self.current_week_monday = today.addDays(-(today.dayOfWeek() - 1))
            
        previous_week = self.current_week_monday
        self.current_week_monday = self.current_week_monday.addDays(7)
        
        self.calendar.setCurrentPage(self.current_week_monday.year(), self.current_week_monday.month())
        
        self.update_calendar_visuals(self.selected_dates, previous_week)
        self.update_summary_view()

    # select_week method is no longer needed as logic is in on_date_clicked and visuals update
    # But let's keep it or remove it? It was used by on_date_clicked before.
    # Now removed.


    def get_summary_key(self):
        if not self.current_week_monday:
            return None
        week_str = self.current_week_monday.toString("yyyy-MM-dd")
        tags = tuple(sorted(self.get_selected_tags()))
        return (week_str, tags)

    def get_tags_filter_str(self):
        """Get tags as comma-separated string for database queries."""
        tags = self.get_selected_tags()
        return ",".join(sorted(tags)) if tags else None

    def update_daily_summary_view(self):
        """Update the daily summary display based on selected date."""
        if len(self.selected_dates) == 1:
            date = list(self.selected_dates)[0]
            date_str = date.toString("yyyy-MM-dd")
            tags_filter = self.get_tags_filter_str()
            
            summary = self.db.get_daily_summary(date_str, tags_filter)
            if summary:
                self.daily_summary_text.setMarkdown(summary)
            else:
                self.daily_summary_text.clear()
                self.daily_summary_text.setPlaceholderText(
                    f"No daily summary for {date_str}. Click 'Generate Daily Summary' to create one."
                )
        else:
            self.daily_summary_text.clear()
            if len(self.selected_dates) > 1:
                self.daily_summary_text.setPlaceholderText("Select a single date to view its summary.")
            else:
                self.daily_summary_text.setPlaceholderText("No date selected.")

    def update_summary_view(self):
        """Update the weekly summary display based on current week."""
        if not self.current_week_monday:
            self.summary_text.clear()
            return
            
        week_str = self.current_week_monday.toString("yyyy-MM-dd")
        tags_filter = self.get_tags_filter_str()
        
        summary = self.db.get_weekly_summary(week_str, tags_filter)
        if summary:
            self.summary_text.setMarkdown(summary)
        else:
            self.summary_text.clear()
            self.summary_text.setPlaceholderText(
                "No summary for this week. Click 'Generate Weekly Summary' to create one."
            )

    def on_generate_daily_summary_clicked(self):
        """Generate summary for the selected date."""
        if len(self.selected_dates) != 1:
            QMessageBox.warning(self, "Select One Date", "Please select exactly one date to generate a daily summary.")
            return
            
        date = list(self.selected_dates)[0]
        date_str = date.toString("yyyy-MM-dd")
        tags = self.get_selected_tags()
        
        recordings = self.db.fetch_by_dates([date_str], tags)
        if not recordings:
            QMessageBox.warning(self, "No Recordings", "No recordings found for the selected date.")
            return
            
        # Prepare text
        full_text = ""
        for rec in recordings:
            full_text += f"\n\n--- Recording: {rec['title'] or 'Untitled'} ({rec['created_at']}) ---\n"
            full_text += rec['transcription'] or ""
            
        if not full_text.strip():
            QMessageBox.warning(self, "No Content", "No transcription content for the selected date.")
            return
            
        # Show progress
        self.progress = QProgressDialog("Generating Daily Summary...", "Cancel", 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.show()
        
        # Validate AI provider
        settings = QSettings("Hectronic", "Secretario")
        from src.ai_provider import validate_ai_provider_config
        is_valid, error_msg = validate_ai_provider_config(settings)
        
        if not is_valid:
            self.progress.close()
            QMessageBox.critical(self, "Error", error_msg)
            return
            
        self.pending_daily_key = (date_str, self.get_tags_filter_str())
        self.worker = AIAssistant("", "daily_summary", full_text)
        self.worker.finished.connect(self.on_summary_finished)
        self.worker.error.connect(self.on_summary_error)
        self.worker.start()

    def on_generate_summary_clicked(self):
        """Generate summary for the CURRENT HIGHLIGHTED WEEK."""
        if not self.current_week_monday:
            QMessageBox.warning(self, "No Week Selected", "Please select a week first.")
            return
            
        week_dates = []
        for i in range(7):
            week_dates.append(self.current_week_monday.addDays(i).toString("yyyy-MM-dd"))
            
        tags = self.get_selected_tags()
        recordings_for_summary = self.db.fetch_by_dates(week_dates, tags)
        
        if not recordings_for_summary:
            QMessageBox.warning(self, "No Recordings", "No recordings found for the highlighted week with selected tags.")
            return

        # Prepare text for summary
        full_text = ""
        for rec in recordings_for_summary:
            full_text += f"\n\n--- Recording: {rec['title'] or 'Untitled'} ({rec['created_at']}) ---\n"
            full_text += rec['transcription'] or ""

        if not full_text.strip():
            QMessageBox.warning(self, "No Content", "The selected recordings have no transcription content.")
            return

        # Show progress
        self.progress = QProgressDialog("Generating Weekly Summary...", "Cancel", 0, 0, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.show()

        # Validate AI provider configuration
        settings = QSettings("Hectronic", "Secretario")
        from src.ai_provider import validate_ai_provider_config
        is_valid, error_msg = validate_ai_provider_config(settings)
        
        if not is_valid:
            self.progress.close()
            QMessageBox.critical(self, "Error", error_msg)
            return

        self.pending_summary_key = self.get_summary_key()
        self.worker = AIAssistant("", "weekly_summary", full_text)
        self.worker.finished.connect(self.on_summary_finished)
        self.worker.error.connect(self.on_summary_error)
        self.worker.start()

    def on_generate_pending_clicked(self):
        """Generate all pending summaries for days and weeks with content."""
        tags_filter = self.get_tags_filter_str()
        
        # Check how many pending items
        pending_daily, pending_weekly = get_pending_summary_counts(tags_filter)
        
        if pending_daily == 0 and pending_weekly == 0:
            QMessageBox.information(self, "All Done", "All days and weeks with content already have summaries!")
            return
            
        # Confirm with user
        msg = f"Found {pending_daily} days and {pending_weekly} weeks without summaries.\n\nDo you want to generate all of them? This may take a while."
        reply = QMessageBox.question(self, "Generate Pending Summaries", msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        # Start generation
        self.pending_progress = QProgressDialog("Generating pending summaries...", "Cancel", 0, pending_daily + pending_weekly, self)
        self.pending_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.pending_progress.show()
        
        self.summary_generator = SummaryGenerator(
            generate_daily=True,
            generate_weekly=True,
            tags_filter=tags_filter,
            parent=self
        )
        self.summary_generator.progress.connect(self.on_pending_progress)
        self.summary_generator.finished.connect(self.on_pending_finished)
        self.summary_generator.error.connect(self.on_pending_error)
        self.pending_progress.canceled.connect(self.summary_generator.cancel)
        self.summary_generator.start()

    def on_pending_progress(self, current, total):
        """Update progress bar for pending generation."""
        if hasattr(self, 'pending_progress'):
            self.pending_progress.setValue(current)

    def on_pending_finished(self, daily_count, weekly_count):
        """Handle completion of pending summary generation."""
        if hasattr(self, 'pending_progress'):
            self.pending_progress.close()
        QMessageBox.information(
            self, "Complete",
            f"Generated {daily_count} daily summaries and {weekly_count} weekly summaries."
        )
        # Refresh views
        self.update_daily_summary_view()
        self.update_summary_view()

    def on_pending_error(self, error_msg):
        """Handle error in pending summary generation."""
        if hasattr(self, 'pending_progress'):
            self.pending_progress.close()
        QMessageBox.critical(self, "Error", f"Summary generation failed: {error_msg}")

    def on_summary_finished(self, task_type, result):
        """Handle completion of a single summary generation."""
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
                # Refresh if still viewing the same date
                if len(self.selected_dates) == 1:
                    current_date = list(self.selected_dates)[0].toString("yyyy-MM-dd")
                    if current_date == date_str:
                        self.update_daily_summary_view()
            self.pending_daily_key = None

    def on_summary_error(self, error_msg):
        """Handle error in summary generation."""
        self.progress.close()
        self.pending_summary_key = None
        self.pending_daily_key = None
        QMessageBox.critical(self, "Error", f"Summary generation failed: {error_msg}")
