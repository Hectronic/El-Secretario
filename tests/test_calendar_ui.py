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
        # Mock new summary methods - return None by default
        self.mock_db.get_daily_summary.return_value = None
        self.mock_db.get_weekly_summary.return_value = None
        
        # Patch QSettings to return auto for compute_type
        self.settings_patcher = patch('src.ui.calendar_widget.QSettings')
        self.mock_settings = self.settings_patcher.start().return_value
        self.mock_settings.value.return_value = "auto"
        
        # Patch RAGEngine
        self.rag = MagicMock()
        
        self.widget = CalendarWidget(self.rag)

    def tearDown(self):
        self.widget.deleteLater()
        self.db_patcher.stop()
        self.settings_patcher.stop()

    def test_initial_selection(self):
        # Initial state should have no dates selected until mandated by sidebar
        self.assertEqual(len(self.widget.selected_dates), 0)
        self.assertIsNone(self.widget.current_anchor_date)
        self.assertIsNone(self.widget.current_week_monday)

    def test_set_selection_day(self):
        # Specific day selection (simulating Ctrl+Click from sidebar)
        date_str = "2026-01-01"
        self.widget.set_selection(None, filter_date=date_str)
        
        self.assertEqual(len(self.widget.selected_dates), 1)
        self.assertIn(QDate.fromString(date_str, "yyyy-MM-dd"), self.widget.selected_dates)
        self.assertEqual(self.widget.current_anchor_date.toString("yyyy-MM-dd"), date_str)
        self.assertIsNone(self.widget.current_week_monday)

    def test_set_selection_week(self):
        # Week selection
        monday = QDate(2026, 1, 5)
        self.widget.set_selection(monday)
        
        self.assertEqual(len(self.widget.selected_dates), 7)
        self.assertEqual(self.widget.current_week_monday, monday)
        # Default anchor for week is Sunday (monday + 6)
        self.assertEqual(self.widget.current_anchor_date, monday.addDays(6))

    def test_set_selection_range(self):
        # Progressive range (Monday -> Target)
        monday = QDate(2026, 1, 5)
        target_str = "2026-01-07" # Wednesday
        self.widget.set_selection(monday, target_str)
        
        self.assertEqual(len(self.widget.selected_dates), 3) # Mon, Tue, Wed
        self.assertIn(QDate(2026, 1, 5), self.widget.selected_dates)
        self.assertIn(QDate(2026, 1, 6), self.widget.selected_dates)
        self.assertIn(QDate(2026, 1, 7), self.widget.selected_dates)

    def test_refresh_tags(self):
        self.mock_db.get_all_tags.return_value = ["NewTag"]
        self.widget.load_tags()
        self.assertEqual(self.widget.tag_list.count(), 1)
        self.assertEqual(self.widget.tag_list.item(0).text(), "NewTag")

    def test_day_navigation(self):
        monday = QDate(2026, 1, 5)
        target_str = "2026-01-07"
        self.widget.set_selection(monday, target_str)
        
        # Navigate forward
        self.widget.navigate_next_day()
        self.assertEqual(self.widget.current_anchor_date.toString("yyyy-MM-dd"), "2026-01-08")
        self.assertEqual(len(self.widget.selected_dates), 4) # Range expanded
        
        # Navigate backward
        self.widget.navigate_prev_day()
        self.assertEqual(self.widget.current_anchor_date.toString("yyyy-MM-dd"), "2026-01-07")
        self.assertEqual(len(self.widget.selected_dates), 3)

    @patch('src.ui.calendar_widget.AIAssistant')
    @patch('src.ui.calendar_widget.QProgressDialog')
    @patch('src.ui.calendar_widget.QMessageBox')
    def test_generate_summary(self, mock_msg, mock_progress, mock_ai_cls):
        # Setup mock AI
        mock_ai = mock_ai_cls.return_value
        
        # Setup selection
        monday = QDate(2026, 1, 5)
        self.widget.set_selection(monday)
        
        self.mock_db.fetch_by_dates.return_value = [
            {'title': 'Rec', 'created_at': '2026-01-05', 'transcription': 'Content', 'tags': ''}
        ]
        
        # Click Generate
        self.widget.on_generate_summary_clicked()
        
        mock_ai.start.assert_called_once()
        
        # Mock get_weekly_summary to return result when called during update_summary_view
        self.mock_db.get_weekly_summary.return_value = "Summary Result"
        self.widget.on_summary_finished("weekly_summary", "Summary Result")
        
        self.mock_db.save_weekly_summary.assert_called_with("2026-01-11", "Summary Result", None)
        self.assertEqual(self.widget.summary_text.toPlainText().strip(), "Summary Result")

    @patch('src.ui.calendar_widget.QMessageBox')
    def test_autonomous_popups(self, mock_msg):
        # Test that click without selection doesn't block (just calls QMessageBox.warning)
        self.widget.selected_dates = set()
        self.widget.on_generate_daily_summary_clicked()
        mock_msg.warning.assert_called()

if __name__ == '__main__':
    unittest.main()
