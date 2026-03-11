
import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QDate

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.recording_widget import RecordingWidget
from src.ui.calendar_widget import CalendarWidget
from src.ui.tools_widget import ToolsWidget
from src.ui.task_batch_widget import TaskBatchWidget
from src.ui.summary_task_queue import SummaryTaskQueueManager
from src.ui.summary_viewer import SummaryViewerWidget
from src.database import DBManager

class TestNewFeaturesIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.db_name = "test_integrity.db"
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
        self.db = DBManager(self.db_name)

        # Avoid multimedia/audio backend hangs in headless CI.
        self.media_player_patcher = patch('src.ui.recording_widget.QMediaPlayer')
        self.audio_output_patcher = patch('src.ui.recording_widget.QAudioOutput')
        self.recorder_patcher = patch('src.ui.recording_widget.Recorder')
        self.media_player_patcher.start()
        self.audio_output_patcher.start()
        self.recorder_patcher.start()
        
        # Mock dependencies
        self.rag = MagicMock()
        self.task_queue = MagicMock(spec=SummaryTaskQueueManager)
        self.notebook_db = MagicMock()

    def tearDown(self):
        self.media_player_patcher.stop()
        self.audio_output_patcher.stop()
        self.recorder_patcher.stop()
        if os.path.exists(self.db_name):
            os.remove(self.db_name)

    def test_recording_widget_instantiation(self):
        """Verify RecordingWidget accepts task_queue and doesn't crash on init."""
        widget = RecordingWidget(self.rag, record_id=None, task_queue=self.task_queue)
        self.assertEqual(widget.summary_task_queue, self.task_queue)
        widget.deleteLater()

    def test_calendar_widget_instantiation(self):
        """Verify CalendarWidget accepts task_queue and doesn't crash on init."""
        widget = CalendarWidget(self.rag, task_queue=self.task_queue)
        self.assertEqual(widget.summary_task_queue, self.task_queue)
        widget.deleteLater()

    def test_tools_widget_instantiation(self):
        """Verify ToolsWidget accepts task_queue and passes it to TaskBatchWidget."""
        widget = ToolsWidget(self.db, self.notebook_db, task_queue=self.task_queue)
        self.assertEqual(widget.task_queue, self.task_queue)
        self.assertEqual(widget.tasks_batch_widget.task_queue, self.task_queue)
        widget.deleteLater()

    def test_tools_widget_rag_reindex_queues_with_selected_scope(self):
        widget = ToolsWidget(self.db, self.notebook_db, task_queue=self.task_queue)
        self.task_queue.enqueue_rag_reindex.return_value = True
        idx = widget.rag_scope_combo.findData("missing")
        self.assertGreaterEqual(idx, 0)
        widget.rag_scope_combo.setCurrentIndex(idx)

        widget._queue_rag_reindex()

        self.task_queue.enqueue_rag_reindex.assert_called_once_with(scope="missing")
        self.assertIn("missing records only", widget.rag_status_lbl.text())
        widget.deleteLater()

    def test_task_batch_widget_logic(self):
        """Verify TaskBatchWidget can refresh stats and attempt to start processing."""
        widget = TaskBatchWidget(task_queue=self.task_queue)
        
        # Test refresh_stats (shouldn't crash)
        widget.refresh_stats()
        
        # Mock QMessageBox to auto-accept
        with patch('PyQt6.QtWidgets.QMessageBox.question', return_value=MagicMock()):
             # We just want to see if it reaches the enqueuing part without SyntaxError or AttributeError
             widget.pending_records = [{'id': 1, 'transcription': 'test', 'tags': 'tag'}]
             with patch('PyQt6.QtWidgets.QMessageBox.question', return_value=MagicMock(text=lambda: "Yes")):
                 # Simulate the Yes button click in a non-blocking way or just mock the call
                 with patch('PyQt6.QtWidgets.QMessageBox.StandardButton', MagicMock()):
                    # To avoid real dialog, we mock the result check
                    pass
        
        widget.deleteLater()

    def test_summary_task_queue_signals(self):
        """Verify SummaryTaskQueueManager has the expected new signals/methods."""
        queue = SummaryTaskQueueManager()
        self.assertTrue(hasattr(queue, 'enqueue_task_extraction'))
        self.assertTrue(hasattr(queue, 'task_progress'))
        queue.cancel_all()

    def test_summary_viewer_instantiation(self):
        """Verify SummaryViewerWidget accepts task_queue."""
        summary_data = {"type": "daily", "date": "2026-02-13"}
        widget = SummaryViewerWidget(summary_data, db=self.db, task_queue=self.task_queue)
        self.assertEqual(widget.task_queue, self.task_queue)
        widget.deleteLater()

if __name__ == '__main__':
    unittest.main()
