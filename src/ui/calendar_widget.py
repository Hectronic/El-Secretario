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

from PyQt6.QtWidgets import QWidget, QListWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from src.database import DBManager
from src.ui.calendar import layout as calendar_layout
from src.ui.calendar import summary_actions

class CalendarWidget(QWidget):
    """
    Renamed to WeekDetailsWidget internally in spirit. 
    Displays recordings and summaries for the selection mandated by the sidebar calendar.
    """
    start_chat_requested = pyqtSignal(str, list) # Emits (date_str_or_list, tags_list)
    selection_changed = pyqtSignal(QDate, str, str)   # Emits (monday, date_str, tags) to sync back to sidebar

    def __init__(self, rag_engine, task_queue=None, parent=None, persistence=None):
        super().__init__(parent)
        self.rag = rag_engine
        self.summary_task_queue = task_queue
        self.db = persistence if persistence is not None else DBManager()
        self.selected_recordings = [] # List of dicts
        self.selected_dates = set() # Set of QDate objects
        self.current_week_monday = None # QDate of the Monday of the currently highlighted week
        self.current_anchor_date = None # QDate of the specific day selection or end of range
        
        self.pending_summary_key = None
        self.pending_daily_key = None
        
        self.init_ui()
        
    def init_ui(self):
        calendar_layout.build_calendar_layout(self)

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
        return summary_actions.on_generate_daily_summary_clicked(self)

    def on_generate_summary_clicked(self):
        return summary_actions.on_generate_summary_clicked(self)

    def on_generate_pending_clicked(self):
        return summary_actions.on_generate_pending_clicked(self)

    def on_pending_progress(self, current, total):
        return summary_actions.on_pending_progress(self, current, total)

    def on_pending_finished(self, daily_count, weekly_count):
        return summary_actions.on_pending_finished(self, daily_count, weekly_count)

    def on_pending_error(self, error_msg):
        return summary_actions.on_pending_error(self, error_msg)

    def on_summary_finished(self, task_type, result):
        return summary_actions.on_summary_finished(self, task_type, result)

    def on_summary_error(self, error_msg):
        return summary_actions.on_summary_error(self, error_msg)
