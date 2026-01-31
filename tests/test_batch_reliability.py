# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call
from PyQt6.QtWidgets import QApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.batch_process_widget import BatchProcessWidget

class TestBatchReliability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.widget = BatchProcessWidget()
        self.widget.db = MagicMock()
        self.widget.log = MagicMock()
        
        # Test record
        self.record_id = 123
        self.record = {
            'id': self.record_id,
            'filename': 'test_audio.wav',
            'duration': 10.0,
            'processing_attempts': 0,
            'last_error': None
        }
        
        # Setup widget state
        self.widget.current_record = self.record
        self.widget.current_item = MagicMock()
        self.widget.queue = [self.record] # Queue holds the record being processed (not popped yet in our test scenario)
        
        # Mock increment_attempt to simulate db value update
        self.widget.db.increment_attempt.side_effect = lambda rid: self.increment_attempts()
        self.current_attempts = 0

    def increment_attempts(self):
        self.current_attempts += 1
        return self.current_attempts

    @patch('PyQt6.QtCore.QTimer.singleShot')
    def test_retry_logic(self, mock_timer):
        # Fail 1st time
        self.widget.on_file_error("Test Error 1")
        
        # Verify attempt incremented and logged
        self.assertEqual(self.current_attempts, 1)
        self.widget.db.set_error.assert_called_with(self.record_id, "Test Error 1")
        self.widget.log.assert_called_with("Retrying... (Attempt 2/3)")
        
        # Verify timer set for retry
        mock_timer.assert_called()
        # Verify queue still has the item (wasn't popped)
        self.assertEqual(len(self.widget.queue), 1)

    def test_max_retries_reached(self):
        self.widget.cleanup_thread = MagicMock() # Mock cleanup
        
        # Simulate already 2 attempts done, failing 3rd time (so attempts becomes 3)
        self.current_attempts = 2 
        
        # Call error
        self.widget.process_next = MagicMock() # Mock process_next to stop recursion
        self.widget.on_file_error("Test Error 3")
        
        # Verify cleanup called
        self.widget.cleanup_thread.assert_called()
        
        # Verify max retries reached logic
        self.assertEqual(self.current_attempts, 3)
        self.widget.log.assert_any_call("Max retries reached. Moving to next file.")
        
        # Verify queue popped (moved to next)
        self.assertEqual(len(self.widget.queue), 0)
        self.widget.process_next.assert_called()

if __name__ == '__main__':
    unittest.main()
