# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.batch_process_widget import BatchProcessWidget


class TestBatchReliability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.db_patcher = patch("src.ui.batch_process_widget.DBManager")
        self.mock_db = self.db_patcher.start().return_value
        self.mock_db.fetch_pending_diarization.return_value = [
            {"id": 123, "filename": "test_audio.wav", "duration": 10.0},
        ]
        self.widget = BatchProcessWidget(task_queue=MagicMock())

    def tearDown(self):
        self.db_patcher.stop()

    def test_start_processing_without_queue_is_blocked(self):
        widget = BatchProcessWidget(task_queue=None)

        widget.start_processing()

        self.assertFalse(widget.start_btn.isEnabled())
        self.assertEqual(widget.status_label.text(), "Task queue is required for batch processing.")

    def test_start_processing_enqueues_batch_jobs_through_central_queue(self):
        self.widget.task_queue.enqueue_transcription.return_value = True

        self.widget.start_processing()

        self.widget.task_queue.enqueue_transcription.assert_called_once()
        call = self.widget.task_queue.enqueue_transcription.call_args
        self.assertEqual(call.args[0], 123)
        self.assertIn("recordings", call.args[1])
        self.assertEqual(call.kwargs["source"], "batch_process")
        self.assertTrue(call.kwargs["diarization"])
        self.assertEqual(call.kwargs["title"], "test_audio.wav")


if __name__ == "__main__":
    unittest.main()
