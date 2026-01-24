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
import numpy as np
from PyQt6.QtWidgets import QApplication
import sys

class TestRecorder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    @patch('src.audio.sd')
    def test_start_stop(self, mock_sd):
        from src.audio import Recorder
        recorder = Recorder()
        recorder.start()
        self.assertTrue(recorder.is_recording)
        self.assertIsNotNone(recorder.stream)
        
        # Mock recording data
        recorder.recording = [np.zeros((100, 1))]
        
        with patch('src.audio.sf.write') as mock_write:
            path = recorder.stop()
            self.assertFalse(recorder.is_recording)
            self.assertIsNotNone(path)
            mock_write.assert_called_once()

    def test_pause_resume(self):
        from src.audio import Recorder
        recorder = Recorder()
        recorder.start()
        recorder.pause()
        self.assertTrue(recorder.is_paused)
        recorder.resume()
        self.assertFalse(recorder.is_paused)

if __name__ == '__main__':
    unittest.main()
