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
from PyQt6.QtWidgets import QApplication, QListWidgetItem
from PyQt6.QtCore import Qt

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.batch_process_widget import BatchProcessWidget

class TestBatchProcess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.db_patcher = patch('src.ui.batch_process_widget.DBManager')
        self.mock_db = self.db_patcher.start().return_value
        self.mock_db.fetch_pending_diarization.return_value = [
            {'id': 1, 'filename': 'rec1.wav', 'duration': 10.0},
            {'id': 2, 'filename': 'rec2.wav', 'duration': 20.0},
            {'id': 3, 'filename': 'rec3.wav', 'duration': 30.0}
        ]
        self.mock_db.increment_attempt.return_value = 3  # Return 3 to trigger max retries path
        self.mock_db.set_error.return_value = None
        
        self.widget = BatchProcessWidget()

    def tearDown(self):
        self.db_patcher.stop()

    def test_load_pending(self):
        # Verify list is populated
        self.assertEqual(self.widget.pending_list.count(), 3)
        self.assertEqual(len(self.widget.queue), 3)
        
    def test_remove_selected(self):
        # Select first item
        self.widget.pending_list.item(0).setSelected(True)
        
        # Remove
        self.widget.remove_selected()
        
        # Verify removed
        self.assertEqual(self.widget.pending_list.count(), 2)
        self.assertEqual(len(self.widget.queue), 2)
        self.assertEqual(self.widget.queue[0]['id'], 2) # rec2 should be first now

    def test_process_next_updates_status(self):
        # Mock os.path.exists to return True
        with patch('os.path.exists', return_value=True):
            # Mock TranscriberThread
            with patch('src.ui.batch_process_widget.TranscriberThread') as mock_thread, \
                 patch('src.ui.batch_process_widget.QSettings') as MockQSettings:
                settings_instance = MagicMock()
                settings_instance.value.side_effect = lambda key, default=None, type=None: {
                    'hf_token': '',
                    'force_cpu': False,
                    'compute_type': 'auto',
                    'transcription_backend': 'auto',
                    'rec_config/model': 'sherpa-onnx',
                    'whisper_model': 'base',
                }.get(key, default)
                MockQSettings.return_value = settings_instance
                self.widget.start_processing()
                
                # Verify item is NOT removed from list yet
                self.assertEqual(self.widget.pending_list.count(), 3)
                # But it should be marked as processing (yellow background)
                item = self.widget.pending_list.item(0)
                self.assertEqual(item.background(), Qt.GlobalColor.yellow)
                self.assertEqual(mock_thread.call_args.kwargs["model_size"], "sherpa-onnx")
                
    def test_on_file_finished_removes_item(self):
        # Setup processing state
        self.widget.is_processing = True
        self.widget.current_record = self.widget.queue[0]
        self.widget.current_item = self.widget.pending_list.item(0)
        
        # Call finished handler
        result = {
            "text": "test", 
            "model_name": "large-v3", 
            "audio_duration": 10.0, 
            "audio_size_bytes": 1000, 
            "transcription_time": 1.0
        }
        
        # Mock process_next to avoid recursion in test
        with patch.object(self.widget, 'process_next') as mock_next:
            self.widget.on_file_finished(result)
            
            # Verify item REMOVED from list
            self.assertEqual(self.widget.pending_list.count(), 2)
            # Verify queue popped (mocked process_next would usually handle the next pop, 
            # but on_file_finished also pops from queue if successful)
            self.assertEqual(len(self.widget.queue), 2)
            
    def test_on_file_error_keeps_item(self):
        # Setup processing state
        self.widget.is_processing = True
        self.widget.current_record = self.widget.queue[0]
        self.widget.current_item = self.widget.pending_list.item(0)
        
        # Mock process_next to avoid recursion
        with patch.object(self.widget, 'process_next') as mock_next:
            self.widget.on_file_error("Some error")
            
            # Verify item KEPT in list
            self.assertEqual(self.widget.pending_list.count(), 3)
            
            # Verify item marked as failed
            item = self.widget.pending_list.item(0)
            self.assertEqual(item.background(), Qt.GlobalColor.red)
            self.assertIn("FAILED", item.text())
            
            # Verify queue popped (to move to next)
            self.assertEqual(len(self.widget.queue), 2)

if __name__ == '__main__':
    unittest.main()
