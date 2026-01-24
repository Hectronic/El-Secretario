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

class TestDeletion(unittest.TestCase):
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
        # Mock delete to return a filename
        self.mock_db.delete.return_value = "test_audio.wav"
        
        self.recorder_patcher = patch('src.ui.main_window.Recorder')
        self.recorder_patcher.start()
        
        # Mock os.remove and os.path.exists
        self.os_remove_patcher = patch('os.remove')
        self.mock_remove = self.os_remove_patcher.start()
        
        self.os_exists_patcher = patch('os.path.exists')
        self.mock_exists = self.os_exists_patcher.start()
        self.mock_exists.return_value = True

        self.window = MainWindow()

    def tearDown(self):
        self.window.close()
        self.rag_patcher.stop()
        self.db_patcher.stop()
        self.recorder_patcher.stop()
        self.os_remove_patcher.stop()
        self.os_exists_patcher.stop()

    def test_delete_recording(self):
        # Simulate delete confirmation
        with patch('PyQt6.QtWidgets.QMessageBox.question', return_value=0x00004000): # Yes button
            self.window.delete_recording(123)
            
            # Verify DB delete called
            self.mock_db.delete.assert_called_with(123)
            
            # Verify File delete called
            # We expect os.remove to be called with the path containing "test_audio.wav"
            self.mock_remove.assert_called()
            args, _ = self.mock_remove.call_args
            self.assertIn("test_audio.wav", args[0])
            
            # Verify RAG delete called
            self.mock_rag.delete_document.assert_called_with("123")

if __name__ == '__main__':
    unittest.main()
