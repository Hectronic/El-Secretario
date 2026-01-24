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
from src.ui.search_results_widget import SearchResultsWidget

class TestSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Patch dependencies
        self.rag_patcher = patch('src.rag_engine.RAGEngine')
        self.mock_rag = self.rag_patcher.start().return_value
        
        self.db_patcher = patch('src.ui.main_window.DBManager')
        self.mock_db = self.db_patcher.start().return_value
        self.mock_db.fetch_all.return_value = []
        
        self.recorder_patcher = patch('src.ui.main_window.Recorder')
        self.recorder_patcher.start()

        self.window = MainWindow()

    def tearDown(self):
        self.window.close()
        self.rag_patcher.stop()
        self.db_patcher.stop()
        self.recorder_patcher.stop()

    def test_search_opens_new_tab(self):
        # Simulate search finished
        results = [{'id': 1, 'text': 'Test Result', 'metadata': {'title': 'Test'}, 'distance': 0.1}]
        query = "test query"
        
        # Call the handler directly to test UI logic (threading is hard to test deterministically)
        self.window.on_search_finished_new_tab(results, query)
        
        # Verify new tab is open
        current_widget = self.window.central_tabs.currentWidget()
        self.assertIsInstance(current_widget, SearchResultsWidget)
        self.assertEqual(self.window.central_tabs.tabText(self.window.central_tabs.currentIndex()), f"Search: {query}")
        
        # Verify results displayed
        self.assertEqual(current_widget.results_list.count(), 1)

    def test_search_error_handler(self):
        # Verify the method exists and doesn't crash
        # We can't easily assert QMessageBox shown without mocking it, but we can ensure the method is callable
        with patch('PyQt6.QtWidgets.QMessageBox.critical') as mock_msg:
            self.window.on_search_error("Test Error")
            mock_msg.assert_called()

if __name__ == '__main__':
    unittest.main()
