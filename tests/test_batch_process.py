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
        self.assertFalse(self.widget.start_btn.isEnabled())
        
    def test_remove_selected(self):
        # Select first item
        self.widget.pending_list.item(0).setSelected(True)
        
        # Remove
        self.widget.remove_selected()
        
        # Verify removed
        self.assertEqual(self.widget.pending_list.count(), 2)
        self.assertEqual(len(self.widget.queue), 2)
        self.assertEqual(self.widget.queue[0]['id'], 2) # rec2 should be first now

    def test_start_processing_requires_task_queue(self):
        self.widget.start_processing()

        self.assertEqual(self.widget.status_label.text(), "Task queue is required for batch processing.")
        self.assertIn("requires the central queue", self.widget.log_text.toPlainText())

    def test_start_processing_via_queue_enables_diarization(self):
        mock_task_queue = MagicMock()
        mock_task_queue.enqueue_transcription.return_value = True
        widget = BatchProcessWidget(task_queue=mock_task_queue)
        widget.queue = [
            {"id": 10, "filename": "a.wav", "duration": 1.0},
            {"id": 11, "filename": "b.wav", "duration": 2.0},
        ]
        widget.start_processing()

        self.assertEqual(mock_task_queue.enqueue_transcription.call_count, 2)
        for call in mock_task_queue.enqueue_transcription.call_args_list:
            self.assertTrue(call.kwargs["diarization"])

    def test_load_pending_marks_fatal_last_error_as_skipped(self):
        self.mock_db.fetch_pending_diarization.return_value = [
            {
                "id": 9,
                "filename": "bad.wav",
                "duration": 4.2,
                "processing_attempts": 3,
                "last_error": "Transcription subprocess timed out.",
            }
        ]

        widget = BatchProcessWidget()

        self.assertEqual(widget.pending_list.count(), 1)
        item = widget.pending_list.item(0)
        self.assertIn("SKIPPED", item.text())
        self.assertEqual(item.background(), Qt.GlobalColor.lightGray)

    def test_load_pending_disables_start_when_queue_missing(self):
        widget = BatchProcessWidget(task_queue=None)
        self.assertFalse(widget.start_btn.isEnabled())
        self.assertEqual(widget.status_label.text(), "Task queue is required for batch processing.")

    def test_queue_task_skipped_updates_current_item_as_skipped(self):
        self.widget.is_processing = True
        self.widget._queued_record_ids = {1}
        self.widget._active_batch_tasks = 1
        self.widget.current_record = {"id": 1, "filename": "rec1.wav"}
        self.widget.current_item = self.widget.pending_list.item(0)

        with patch.object(self.widget, "_finish_queue_mode_if_done") as mock_done:
            self.widget._on_queue_task_skipped(
                {
                    "source": "batch_process",
                    "type": "transcription",
                    "record_id": 1,
                    "title": "rec1.wav",
                },
                "Transcription subprocess timed out.",
            )

        self.assertNotIn(1, self.widget._queued_record_ids)
        self.assertIn("SKIPPED", self.widget.pending_list.item(0).text())
        self.assertEqual(self.widget.pending_list.item(0).background(), Qt.GlobalColor.lightGray)
        self.assertEqual(self.widget.processed_count, 1)
        mock_done.assert_called_once()

    def test_queue_task_failed_updates_current_item_and_progress(self):
        self.widget.is_processing = True
        self.widget._queued_record_ids = {1}
        self.widget._active_batch_tasks = 1
        self.widget.current_record = {"id": 1, "filename": "rec1.wav"}
        self.widget.current_item = self.widget.pending_list.item(0)

        with patch.object(self.widget, "_finish_queue_mode_if_done") as mock_done:
            self.widget._on_queue_task_failed(
                {
                    "source": "batch_process",
                    "type": "transcription",
                    "record_id": 1,
                    "title": "rec1.wav",
                },
                "Some recoverable error",
            )

        self.assertNotIn(1, self.widget._queued_record_ids)
        self.assertIn("FAILED", self.widget.pending_list.item(0).text())
        self.assertEqual(self.widget.processed_count, 1)
        mock_done.assert_called_once()

    def test_duplicate_terminal_signals_for_same_batch_task_are_counted_once(self):
        self.widget.is_processing = True
        self.widget._queued_record_ids = {1, 2}
        self.widget._active_batch_tasks = 2
        self.widget.total_files = 2
        self.widget.processed_count = 0

        skipped_task = {
            "source": "batch_process",
            "type": "transcription",
            "record_id": 1,
            "title": "rec1.wav",
        }

        with patch.object(self.widget, "_finish_queue_mode_if_done"):
            self.widget._on_queue_task_skipped(skipped_task, "Transcription subprocess timed out.")
        self.widget._on_queue_task_finished(skipped_task)

        self.assertEqual(self.widget._active_batch_tasks, 1)
        self.assertEqual(self.widget.processed_count, 1)
        self.assertNotIn(1, self.widget._queued_record_ids)

if __name__ == '__main__':
    unittest.main()
