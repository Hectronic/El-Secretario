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

from src.ui.recording_widget import RecordingWidget

class TestDiarizationToggle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.db_patcher = patch('src.ui.recording_widget.DBManager')
        self.mock_db = self.db_patcher.start().return_value
        record = {'id': 1, 'filename': 'test.wav', 'transcription': 'test', 'is_diarized': 0, 'transcription_model': 'base', 'title': 'Test', 'tags': '', 'cleaned_text': '', 'summary': '', 'created_at': '2023-01-01', 'duration': 10.0}
        self.mock_db.fetch_all.return_value = [record]
        self.mock_db.fetch_record.return_value = record
        self.mock_db.get_all_tags.return_value = []

        self.media_player_patcher = patch('src.ui.recording_widget.QMediaPlayer')
        self.audio_output_patcher = patch('src.ui.recording_widget.QAudioOutput')
        self.media_player_patcher.start()
        self.audio_output_patcher.start()
        
        self.recorder_patcher = patch('src.ui.recording_widget.Recorder')
        self.recorder_patcher.start()
        
        self.rag_patcher = patch('src.rag_engine.RAGEngine')
        self.mock_rag = self.rag_patcher.start().return_value

        self.mock_queue = MagicMock()
        self.widget = RecordingWidget(self.mock_rag, record_id=1, task_queue=self.mock_queue)

    def tearDown(self):
        self.widget.close()
        self.widget.deleteLater()
        self.db_patcher.stop()
        self.media_player_patcher.stop()
        self.audio_output_patcher.stop()
        self.recorder_patcher.stop()
        self.rag_patcher.stop()

    def test_toggle_diarization(self):
        # Verify initial state
        self.assertFalse(self.widget.is_diarized_check_meta.isChecked())
        self.assertTrue(self.widget.is_diarized_check_meta.isEnabled())
        
        # Toggle checkbox
        self.widget.is_diarized_check_meta.setChecked(True)
        
        # Save
        self.widget.save_all_changes()
        
        # Verify DB update called with is_diarized=True
        # We need to check the call args to update_transcription
        args, kwargs = self.mock_db.update_transcription.call_args
        self.assertEqual(args[0], 1) # record_id
        self.assertEqual(kwargs['is_diarized'], True)

if __name__ == '__main__':
    unittest.main()
