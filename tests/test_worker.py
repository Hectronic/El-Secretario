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

import unittest
from unittest.mock import MagicMock, patch
from src.worker import TranscriberThread
import os

class TestTranscriberThread(unittest.TestCase):
    @patch('src.worker.WhisperModel')
    @patch('os.path.getsize')
    def test_transcription(self, mock_getsize, MockWhisper):
        # Setup Mock
        mock_getsize.return_value = 1024
        mock_model = MockWhisper.return_value
        Segment = MagicMock()
        Segment.start = 0.0
        Segment.end = 1.0
        Segment.text = "Hello world"
        
        mock_model.transcribe.return_value = ([Segment], None)
        
        thread = TranscriberThread("test.wav")
        
        # Mock signals
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()
        
        thread.run()
        
        # Verify finished signal called with a dict containing the text
        args, _ = thread.finished.emit.call_args
        result = args[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result['text'], "Hello world")

if __name__ == '__main__':
    unittest.main()
