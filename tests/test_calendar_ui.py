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

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QDate

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.calendar_widget import CalendarWidget

class TestCalendarUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Patch DBManager
        self.db_patcher = patch('src.ui.calendar_widget.DBManager')
        self.mock_db_cls = self.db_patcher.start()
        self.mock_db = self.mock_db_cls.return_value
        self.mock_db.get_all_tags.return_value = ["Tag1", "Tag2"]
        self.mock_db.fetch_by_dates.return_value = []
        
        # Patch RAGEngine
        self.rag = MagicMock()
        
        self.widget = CalendarWidget(self.rag)

    def tearDown(self):
        self.widget.deleteLater()
        self.db_patcher.stop()

    def test_initial_selection(self):
        # Should have today selected by default
        today = QDate.currentDate()
        self.assertIn(today, self.widget.selected_dates)
        self.assertEqual(self.widget.last_clicked_date, today)
        
        # Should have current week set
        day_of_week = today.dayOfWeek()
        expected_monday = today.addDays(-(day_of_week - 1))
        self.assertEqual(self.widget.current_week_monday, expected_monday)

    def test_single_click(self):
        # Click a date
        date = QDate(2026, 1, 1) # Thursday
        # Mock modifiers to be NoModifier
        with patch('PyQt6.QtWidgets.QApplication.keyboardModifiers', return_value=Qt.KeyboardModifier.NoModifier):
            self.widget.on_date_clicked(date)
        
        # Should select ONLY that date
        self.assertEqual(len(self.widget.selected_dates), 1)
        self.assertIn(date, self.widget.selected_dates)
        
        # But should update current week
        # Jan 1 2026 is Thursday. Monday is Dec 29 2025.
        expected_monday = QDate(2025, 12, 29)
        self.assertEqual(self.widget.current_week_monday, expected_monday)
            
        self.assertEqual(self.widget.last_clicked_date, date)

    def test_ctrl_click_toggle(self):
        date1 = QDate(2026, 1, 1)
        date2 = QDate(2026, 1, 2)
        
        # Select date1 (Week of Dec 29 - Jan 4)
        with patch('PyQt6.QtWidgets.QApplication.keyboardModifiers', return_value=Qt.KeyboardModifier.NoModifier):
            self.widget.on_date_clicked(date1)
        
        # Should have 1 day selected
        self.assertEqual(len(self.widget.selected_dates), 1)
            
        # Ctrl+Click date2 (Same week)
        with patch('PyQt6.QtWidgets.QApplication.keyboardModifiers', return_value=Qt.KeyboardModifier.ControlModifier):
            self.widget.on_date_clicked(date2)
            
        # Should have 2 days selected
        self.assertEqual(len(self.widget.selected_dates), 2)
        self.assertIn(date1, self.widget.selected_dates)
        self.assertIn(date2, self.widget.selected_dates)
        
        # Ctrl+Click date1 again to toggle off
        with patch('PyQt6.QtWidgets.QApplication.keyboardModifiers', return_value=Qt.KeyboardModifier.ControlModifier):
            self.widget.on_date_clicked(date1)
            
        self.assertEqual(len(self.widget.selected_dates), 1)
        self.assertIn(date2, self.widget.selected_dates)
        self.assertNotIn(date1, self.widget.selected_dates)

    def test_shift_click_range(self):
        date1 = QDate(2026, 1, 1) # Thursday
        date5 = QDate(2026, 1, 8) # Next Thursday
        
        # Select date1 (Week 1)
        with patch('PyQt6.QtWidgets.QApplication.keyboardModifiers', return_value=Qt.KeyboardModifier.NoModifier):
            self.widget.on_date_clicked(date1)
            
        # Shift+Click date5
        with patch('PyQt6.QtWidgets.QApplication.keyboardModifiers', return_value=Qt.KeyboardModifier.ShiftModifier):
            self.widget.on_date_clicked(date5)
            
        # Range from last_clicked (Jan 1) to Jan 8.
        # Jan 1 to Jan 8 is 8 days.
        # Initial click selected Jan 1.
        # Shift click adds range [min, max] to existing selection.
        # Existing: {Jan 1}
        # Added: {Jan 1, ..., Jan 8}
        # Union: {Jan 1, ..., Jan 8} -> 8 days.
        
        self.assertEqual(len(self.widget.selected_dates), 8)
        self.assertIn(QDate(2026, 1, 8), self.widget.selected_dates)

    def test_refresh_tags(self):
        self.mock_db.get_all_tags.return_value = ["NewTag"]
        self.widget.load_tags()
        self.assertEqual(self.widget.tag_list.count(), 1)
        self.assertEqual(self.widget.tag_list.item(0).text(), "NewTag")

    def test_week_navigation(self):
        # Set initial date
        initial_date = QDate(2026, 1, 1) # Thursday
        self.widget.last_clicked_date = initial_date
        self.widget.calendar.setSelectedDate(initial_date)
        self.widget.selected_dates.clear() # Clear default selection
        
        # Set initial week
        self.widget.current_week_monday = QDate(2025, 12, 29)
        
        # Click Next Week
        self.widget.on_next_week_clicked()
        
        # Should update current week
        expected_monday = QDate(2026, 1, 5)
        self.assertEqual(self.widget.current_week_monday, expected_monday)
        
        # Selection should NOT change (still just initial_date if it was selected, or whatever)
        # In this test setup, we didn't explicitly select initial_date in widget.selected_dates
        # But let's verify selected_dates is empty (default) or unchanged
        self.assertEqual(len(self.widget.selected_dates), 0)
            
        # Click Prev Week
        self.widget.on_prev_week_clicked()
        expected_monday = QDate(2025, 12, 29)
        self.assertEqual(self.widget.current_week_monday, expected_monday)

    @patch('src.ui.calendar_widget.AIAssistant')
    @patch('src.ui.calendar_widget.QProgressDialog')
    @patch('src.ui.calendar_widget.QMessageBox')
    @patch('src.ui.calendar_widget.QSettings')
    def test_generate_summary(self, mock_settings_cls, mock_msg, mock_progress, mock_ai_cls):
        # Mock Settings
        mock_settings = mock_settings_cls.return_value
        mock_settings.value.side_effect = lambda key, default: "fake_key_from_settings" if key == "gemini_key" else default
        # Setup mock AI
        mock_ai = mock_ai_cls.return_value
        
        # Setup mock DB to return recordings for the week
        # We need to mock fetch_by_dates to return something when called with week dates
        # The widget calculates week dates from current_week_monday
        self.widget.current_week_monday = QDate(2026, 1, 1) # Thursday, so Monday is Dec 29
        # But for simplicity let's just say current_week_monday is Jan 1 (if it was Monday)
        # Actually logic is: current_week_monday is always Monday.
        self.widget.current_week_monday = QDate(2025, 12, 29)
        
        self.mock_db.fetch_by_dates.return_value = [
            {'title': 'Rec Week', 'created_at': '2026-01-01', 'transcription': 'Content Week', 'tags': ''}
        ]
        
        # Click Generate
        self.widget.on_generate_summary_clicked()
        
        # Verify AI started with correct content
        mock_ai_cls.assert_called_with("fake_key_from_settings", "weekly_summary", "\n\n--- Recording: Rec Week (2026-01-01) ---\nContent Week")
        mock_ai.start.assert_called_once()
        
        # Simulate finish
        self.widget.on_summary_finished("weekly_summary", "Summary Result")
        self.assertEqual(self.widget.summary_text.toMarkdown().strip(), "Summary Result")

    @patch('src.ui.calendar_widget.AIAssistant')
    @patch('src.ui.calendar_widget.QProgressDialog')
    @patch('src.ui.calendar_widget.QMessageBox')
    @patch('src.ui.calendar_widget.QSettings')
    def test_summary_caching(self, mock_settings_cls, mock_msg, mock_progress, mock_ai_cls):
        # Mock Settings
        mock_settings = mock_settings_cls.return_value
        mock_settings.value.side_effect = lambda key, default: "fake_key" if key == "gemini_key" else default
        
        # Setup mock AI
        mock_ai = mock_ai_cls.return_value
        
        # Setup DB for week
        self.widget.current_week_monday = QDate(2026, 1, 1)
        self.mock_db.fetch_by_dates.return_value = [{'title': 'T', 'created_at': 'D', 'transcription': 'C', 'tags': ''}]
        
        # 1. Generate Global Summary
        self.widget.on_generate_summary_clicked()
        self.widget.on_summary_finished("weekly_summary", "Global Summary")
        self.assertEqual(self.widget.summary_text.toMarkdown().strip(), "Global Summary")
        
        # 2. Select a Tag
        # Mock tag selection
        with patch.object(self.widget, 'get_selected_tags', return_value=['Tag1']):
            # Trigger tag change
            self.widget.on_tag_changed(None)
            
            # Should be empty initially
            self.assertEqual(self.widget.summary_text.toMarkdown().strip(), "")
            
            # Generate Tagged Summary
            self.widget.on_generate_summary_clicked()
            self.widget.on_summary_finished("weekly_summary", "Tag1 Summary")
            self.assertEqual(self.widget.summary_text.toMarkdown().strip(), "Tag1 Summary")
            
        # 3. Switch back to Global (no tags)
        # Mock tag selection returning empty
        with patch.object(self.widget, 'get_selected_tags', return_value=[]):
            self.widget.on_tag_changed(None)
            # Should restore Global Summary from cache
            self.assertEqual(self.widget.summary_text.toMarkdown().strip(), "Global Summary")
            
        # 4. Switch back to Tag1
        with patch.object(self.widget, 'get_selected_tags', return_value=['Tag1']):
            self.widget.on_tag_changed(None)
            # Should restore Tag1 Summary from cache
            self.assertEqual(self.widget.summary_text.toMarkdown().strip(), "Tag1 Summary")

if __name__ == '__main__':
    unittest.main()
