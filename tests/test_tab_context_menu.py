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
from PyQt6.QtWidgets import QApplication, QWidget

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.main_window import MainWindow

class TestTabContextMenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Patch dependencies to avoid complex init
        self.db_patcher = patch('src.ui.main_window.DBManager')
        self.mock_db = self.db_patcher.start().return_value
        
        self.recorder_patcher = patch('src.ui.main_window.Recorder')
        self.mock_recorder = self.recorder_patcher.start().return_value

        self.mock_rag = MagicMock()
        # MainWindow init doesn't take rag_engine, it initializes it internally or we set it later
        self.window = MainWindow()
        self.window.rag = self.mock_rag
        
        # Clear existing tabs (Welcome tab might be there)
        self.window.central_tabs.clear()
        
        # Add dummy tabs
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.window.central_tabs.addTab(self.tab1, "Tab 1")
        self.window.central_tabs.addTab(self.tab2, "Tab 2")
        self.window.central_tabs.addTab(self.tab3, "Tab 3")

    def tearDown(self):
        self.db_patcher.stop()
        self.recorder_patcher.stop()
        self.window.close()

    def test_close_all_tabs(self):
        self.assertEqual(self.window.central_tabs.count(), 3)
        self.window.close_all_tabs()
        # Should be 1 because close_all_tabs calls show_welcome_screen if empty
        self.assertEqual(self.window.central_tabs.count(), 1)
        self.assertEqual(self.window.central_tabs.tabText(0), "Welcome")

    def test_close_other_tabs(self):
        self.assertEqual(self.window.central_tabs.count(), 3)
        # Keep Tab 2 (index 1)
        self.window.close_other_tabs(1)
        
        self.assertEqual(self.window.central_tabs.count(), 1)
        self.assertEqual(self.window.central_tabs.widget(0), self.tab2)

    def test_close_tab(self):
        self.assertEqual(self.window.central_tabs.count(), 3)
        # Close Tab 2 (index 1)
        self.window.close_tab(1)
        
        self.assertEqual(self.window.central_tabs.count(), 2)
        self.assertEqual(self.window.central_tabs.widget(0), self.tab1)
        self.assertEqual(self.window.central_tabs.widget(1), self.tab3)

if __name__ == '__main__':
    unittest.main()
