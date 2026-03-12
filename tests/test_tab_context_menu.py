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
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.main_window import MainWindow
from src.ui.chat_widget import ChatWidget
from src.ui.styles import apply_theme

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
        self.chat_db_patcher = patch("src.ui.chat_widget.DBManager")
        self.mock_chat_db = self.chat_db_patcher.start().return_value
        self.chat_nb_patcher = patch("src.ui.chat_widget.NotebookDBManager")
        self.mock_chat_nb = self.chat_nb_patcher.start().return_value

        self.mock_db.fetch_chat_sessions.return_value = []
        self.mock_db.get_notebooks.return_value = []
        self.mock_chat_db.fetch_chat_sessions.return_value = []
        self.mock_chat_db.fetch_by_date_range.return_value = []
        self.mock_chat_db.fetch_by_dates.return_value = []
        self.mock_chat_nb.get_notebooks.return_value = []

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
        self.chat_db_patcher.stop()
        self.chat_nb_patcher.stop()
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

    def test_chat_can_move_between_tab_and_floating_bar(self):
        self.window.central_tabs.clear()
        chat_widget = ChatWidget(self.mock_rag)
        self.window._connect_chat_widget(chat_widget)
        self.window.central_tabs.addTab(chat_widget, "Chat")

        self.window.float_chat_widget(chat_widget)
        self.assertEqual(self.window.central_tabs.count(), 0)
        self.assertEqual(len(self.window.floating_chat_hosts), 1)
        self.assertFalse(self.window.floating_chat_bar.isHidden())
        self.assertIs(self.window.floating_chat_bar.parentWidget(), self.window.centralWidget())
        self.assertEqual(chat_widget.display_mode, "floating")
        self.assertTrue(chat_widget.context_panel.isHidden())

        self.window.dock_chat_widget_to_tab(chat_widget)
        self.assertEqual(self.window.central_tabs.count(), 1)
        self.assertEqual(len(self.window.floating_chat_hosts), 0)
        self.assertTrue(self.window.floating_chat_bar.isHidden())
        self.assertEqual(chat_widget.display_mode, "tab")
        self.assertFalse(chat_widget.context_panel.isHidden())

    def test_floating_chat_can_be_minimized_to_title_bar_and_restored(self):
        self.window.central_tabs.clear()
        chat_widget = ChatWidget(self.mock_rag)
        self.window._connect_chat_widget(chat_widget)
        self.window.central_tabs.addTab(chat_widget, "Chat")

        self.window.float_chat_widget(chat_widget)
        host = self.window.floating_chat_hosts[0]

        self.window.minimize_floating_chat(chat_widget)
        self.assertTrue(host.property("chat_minimized"))
        self.assertFalse(chat_widget.isHidden())
        self.assertTrue(chat_widget.content_container.isHidden())
        self.assertEqual(host.height(), 32)

        QTest.mouseClick(chat_widget.header, Qt.MouseButton.LeftButton)
        self.assertFalse(host.property("chat_minimized"))
        self.assertFalse(chat_widget.isHidden())
        self.assertFalse(chat_widget.content_container.isHidden())

    def test_multiple_floating_chats_align_side_by_side_on_bottom_edge(self):
        self.window.central_tabs.clear()
        chat_widget_1 = ChatWidget(self.mock_rag)
        chat_widget_2 = ChatWidget(self.mock_rag)
        self.window._connect_chat_widget(chat_widget_1)
        self.window._connect_chat_widget(chat_widget_2)
        self.window.central_tabs.addTab(chat_widget_1, "Chat 1")
        self.window.central_tabs.addTab(chat_widget_2, "Chat 2")

        self.window.float_chat_widget(chat_widget_1)
        self.window.float_chat_widget(chat_widget_2)
        
        # In headless tests, geometry might not be calculated, so we check layout containment
        self.assertEqual(self.window.floating_chat_layout.count(), 2)
        self.assertFalse(self.window.floating_chat_bar.isHidden())
        
        host_1 = self.window.floating_chat_hosts[0]
        host_2 = self.window.floating_chat_hosts[1]
        
        self.assertIs(self.window.floating_chat_layout.itemAt(0).widget(), host_1)
        self.assertIs(self.window.floating_chat_layout.itemAt(1).widget(), host_2)
        self.assertEqual(host_1.y() + host_1.height(), host_2.y() + host_2.height())

    def test_floating_chat_host_updates_for_dark_theme(self):
        apply_theme("Dark")
        self.window.central_tabs.clear()
        chat_widget = ChatWidget(self.mock_rag)
        self.window._connect_chat_widget(chat_widget)
        self.window.central_tabs.addTab(chat_widget, "Chat")

        self.window.float_chat_widget(chat_widget)
        host = self.window.floating_chat_hosts[0]
        self.app.processEvents()

        self.assertIn("background-color: #232831", host.styleSheet())
        self.assertIn("border: 1px solid rgba(100, 181, 246, 0.55)", host.styleSheet())
        self.assertIn("background-color: #1f232a", chat_widget.display.styleSheet())

        apply_theme("Light")

if __name__ == '__main__':
    unittest.main()
