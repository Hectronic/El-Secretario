import unittest
import os
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QTimer, QCoreApplication
from src.ui.summary_task_queue import SummaryTaskQueueManager
from src.database import DBManager

class TestSummaryQueue(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_queue_db.sqlite"
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
        
        self.db = DBManager(self.db_name)
        # Avoid the real DB init by patching before init
        with patch('src.ui.summary_task_queue.DBManager') as mock_db_class:
            self.queue_manager = SummaryTaskQueueManager()
            self.queue_manager.db = self.db

    def tearDown(self):
        self.queue_manager.cancel_all()
        if os.path.exists(self.db_name):
            os.remove(self.db_name)

    def test_enqueue_recording_summary(self):
        # Mock AIAssistant to avoid actual AI calls
        with patch('src.ui.summary_task_queue.AIAssistant') as MockAI:
            mock_worker = MagicMock()
            MockAI.return_value = mock_worker
            
            # First task
            self.queue_manager.enqueue_recording_summary(1, "text 1", "title 1")
            self.assertEqual(self.queue_manager.pending_count, 1)
            self.assertTrue(self.queue_manager.is_running)
            
            # Second task
            self.queue_manager.enqueue_recording_summary(2, "text 2", "title 2")
            self.assertEqual(self.queue_manager.pending_count, 2)
            
            # Verify AIAssistant was instantiated for the first task
            MockAI.assert_called_once_with("", "summary", "text 1")

    def test_persistence_on_finish(self):
        # Create a record in the test DB
        record_id = self.db.save("test.wav", "Transcription", 10.0, "Title")
        
        with patch('src.ui.summary_task_queue.AIAssistant') as MockAI:
            mock_worker = MagicMock()
            MockAI.return_value = mock_worker
            
            self.queue_manager.enqueue_recording_summary(record_id, "Transcription", "Title")
            
            # Find the callback for task_completed
            task_completed_callback = None
            for call in mock_worker.task_completed.connect.call_args_list:
                task_completed_callback = call.args[0]
                break
            
            self.assertIsNotNone(task_completed_callback)
            task_completed_callback("summary", "Generated Summary")
            
            # Verify DB was updated
            record = self.db.fetch_record(record_id)
            self.assertEqual(record['summary'], "Generated Summary")

    def test_deduplication(self):
        with patch('src.ui.summary_task_queue.AIAssistant'):
            self.queue_manager.enqueue_recording_summary(1, "text 1", "title 1")
            self.assertEqual(self.queue_manager.pending_count, 1)
            
            # Enqueue same task again
            result = self.queue_manager.enqueue_recording_summary(1, "text 1", "title 1")
            self.assertFalse(result)
            self.assertEqual(self.queue_manager.pending_count, 1)

    def test_task_extraction_persistence(self):
        record_id = self.db.save("test.wav", "Transcription", 10.0, "Title")
        self.db.update_tags(record_id, "tag1, tag2")
        
        with patch('src.ui.summary_task_queue.AIAssistant') as MockAI:
            mock_worker = MagicMock()
            MockAI.return_value = mock_worker
            
            # Enqueue task extraction directly
            self.queue_manager.enqueue_task_extraction(record_id, "Transcription", "tag1, tag2")
            
            # Find callback
            task_completed_callback = None
            for call in mock_worker.task_completed.connect.call_args_list:
                task_completed_callback = call.args[0]
                break
            
            self.assertIsNotNone(task_completed_callback)
            
            # Simulate JSON result
            json_tasks = '["Task 1", "Task 2"]'
            task_completed_callback("task_extraction", json_tasks)
            
            # Verify DB
            tasks = self.db.get_tasks_by_record(record_id)
            self.assertEqual(len(tasks), 2)
            self.assertEqual(tasks[0]['content'], "Task 1")
            self.assertEqual(tasks[0]['tags'], "tag1, tag2")
            self.assertEqual(tasks[1]['content'], "Task 2")

    def test_task_extraction_queue_has_title(self):
        record_id = self.db.save("test.wav", "Transcription", 10.0, "My Recording")
        self.queue_manager.enqueue_task_extraction(record_id, "Transcription", "tag1")
        queued = self.queue_manager.get_current_task() or {}
        self.assertEqual(queued.get("type"), "task_extraction")
        self.assertEqual(queued.get("title"), "My Recording")

    def test_daily_summary_enqueues_pending_recording_summaries_first(self):
        rec1 = self.db.save("a.wav", "Tx A", 10.0, "A")
        rec2 = self.db.save("b.wav", "Tx B", 10.0, "B")
        self.db.update_ai_content(rec1, summary="Already done")

        with patch('src.ui.summary_task_queue.AIAssistant'):
            self.queue_manager.enqueue_daily_summary({"date": "2026-02-27", "tags_filter": ""})
            queued = self.queue_manager.get_queue_list()
            current = self.queue_manager.get_current_task() or {}
            all_tasks = [current] + queued
            # rec2 summary should be pending in queue and daily summary should also exist.
            self.assertTrue(any(t.get("type") == "summary" and t.get("record_id") == rec2 for t in all_tasks))
            self.assertTrue(any(t.get("type") == "daily_summary" and t.get("date") == "2026-02-27" for t in all_tasks))

    def test_session_history_records_queue_events(self):
        with patch('src.ui.summary_task_queue.AIAssistant'):
            self.queue_manager.enqueue_recording_summary(1, "text 1", "title 1")
            history = self.queue_manager.get_session_history()
            events = [entry.get("event") for entry in history]
            self.assertIn("queued", events)
            self.assertIn("started", events)

    def test_external_trace_is_added_to_session_history(self):
        self.queue_manager.add_external_trace(
            "Retrying transcription with safer profile",
            {"type": "transcription", "record_id": 99},
            event="trace",
        )
        history = self.queue_manager.get_session_history()
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0].get("event"), "trace")
        self.assertIn("Retrying transcription", history[0].get("message", ""))

    def test_worker_status_updates_append_trace_once_for_duplicates(self):
        self.queue_manager._current_task = {"type": "transcription", "record_id": 77}
        self.queue_manager._on_worker_status_update("Retrying 1")
        self.queue_manager._on_worker_status_update("Retrying 1")
        self.queue_manager._on_worker_status_update("Retrying 2")

        history = self.queue_manager.get_session_history()
        traces = [h for h in history if h.get("event") == "trace"]
        messages = [h.get("message") for h in traces]
        self.assertEqual(messages.count("Retrying 1"), 1)
        self.assertEqual(messages.count("Retrying 2"), 1)

    def test_enqueue_rag_reindex_deduplicates_by_scope(self):
        with patch.object(self.queue_manager, "_start_next_if_idle"):
            self.assertTrue(self.queue_manager.enqueue_rag_reindex(scope="all"))
            self.assertTrue(self.queue_manager.enqueue_rag_reindex(scope="missing"))
            self.assertFalse(self.queue_manager.enqueue_rag_reindex(scope="missing"))

            queued = self.queue_manager.get_queue_list()
            self.assertEqual(len(queued), 2)
            scopes = sorted([q.get("reindex_scope") for q in queued])
            self.assertEqual(scopes, ["all", "missing"])

if __name__ == '__main__':
    unittest.main()
