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

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.main_window import MainWindow
from src.ui.calendar_widget import CalendarWidget

class TestCalendarButton(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Patch dependencies
        self.rag_patcher = patch('src.rag_engine.RAGEngine')
        self.rag_patcher.start()
        
        self.db_patcher = patch('src.ui.main_window.DBManager')
        self.mock_db = self.db_patcher.start().return_value
        self.mock_db.fetch_all.return_value = []
        self.mock_db.get_all_tags.return_value = []
        
        self.recorder_patcher = patch('src.ui.main_window.Recorder')
        self.recorder_patcher.start()

        self.window = MainWindow()

    def tearDown(self):
        self.window.close()
        self.rag_patcher.stop()
        self.db_patcher.stop()
        self.recorder_patcher.stop()

    def test_open_calendar_tab(self):
        # 1. Click the button
        self.window.open_calendar_btn.click()
        
        # 2. Verify tab is open
        current_widget = self.window.central_tabs.currentWidget()
        self.assertIsInstance(current_widget, CalendarWidget)
        self.assertEqual(self.window.central_tabs.tabText(self.window.central_tabs.currentIndex()), "Calendar")
        
        # 3. Click again, should not open duplicate
        count_before = self.window.central_tabs.count()
        self.window.open_calendar_btn.click()
        count_after = self.window.central_tabs.count()
        self.assertEqual(count_before, count_after)

if __name__ == '__main__':
    unittest.main()
