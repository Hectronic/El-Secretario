import unittest
import os
import tempfile
from unittest.mock import MagicMock, patch
from src.ui.summary_task_queue import (
    SummaryTaskQueueManager,
    _parse_task_extraction_result,
    _read_audio_duration_seconds,
)
from src.database import DBManager

class TestSummaryQueue(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="summary_queue_test_")
        self.db_name = os.path.join(self.tmp_dir.name, "queue.sqlite")
        
        self.db = DBManager(self.db_name)
        # Avoid the real DB init by patching before init
        with patch('src.ui.summary_task_queue.DBManager') as mock_db_class:
            self.queue_manager = SummaryTaskQueueManager()
            self.queue_manager.db = self.db

    def tearDown(self):
        self.queue_manager.cancel_all()
        self.tmp_dir.cleanup()

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

    def test_task_extraction_result_parser_accepts_wrapped_json(self):
        result = _parse_task_extraction_result("Here are the tasks:\n[\"Task 1\", \"\", \"Task 2\"]")

        self.assertEqual(result, ["Task 1", "Task 2"])

    def test_task_extraction_result_parser_returns_empty_for_invalid_payload(self):
        self.assertEqual(_parse_task_extraction_result("not json"), [])

    @patch("src.ui.summary_task_queue.logging.warning")
    def test_read_audio_duration_seconds_returns_zero_when_probe_fails(self, mock_warning):
        duration = _read_audio_duration_seconds("/tmp/does-not-exist.wav")

        self.assertEqual(duration, 0.0)
        mock_warning.assert_called_once()

    def test_task_extraction_queue_has_title(self):
        record_id = self.db.save("test.wav", "Transcription", 10.0, "My Recording")
        with patch('src.ui.summary_task_queue.AIAssistant'):
            self.queue_manager.enqueue_task_extraction(record_id, "Transcription", "tag1")
        queued = self.queue_manager.get_current_task() or {}
        self.assertEqual(queued.get("type"), "task_extraction")
        self.assertEqual(queued.get("title"), "My Recording")

    def test_daily_summary_only_enqueues_daily_summary_task(self):
        with patch.object(self.queue_manager, "_start_next_if_idle"):
            self.queue_manager.enqueue_daily_summary({"date": "2026-02-27", "tags_filter": ""})
            queued = self.queue_manager.get_queue_list()
            current = self.queue_manager.get_current_task() or {}
            all_tasks = [current] + queued
            self.assertTrue(any(t.get("type") == "daily_summary" and t.get("date") == "2026-02-27" for t in all_tasks))
            self.assertFalse(any(t.get("type") == "summary" for t in all_tasks))

    def test_task_extraction_is_skipped_when_tasks_already_exist(self):
        record_id = self.db.save("test.wav", "Transcription", 10.0, "Title")
        self.db.save_task(record_id=record_id, content="Existing task", tags="tag1", is_ai_generated=True)

        with patch('src.ui.summary_task_queue.AIAssistant') as MockAI:
            result = self.queue_manager.enqueue_task_extraction(record_id, "Transcription", "tag1", "Title")

        self.assertFalse(result)
        MockAI.assert_not_called()
        tasks = self.db.get_tasks_by_record(record_id)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["content"], "Existing task")

    def test_daily_summary_completed_recording_can_enqueue_task_extraction_once(self):
        record_id = self.db.save("test.wav", "Transcription", 10.0, "Title")

        with patch.object(self.queue_manager, "enqueue_task_extraction") as enqueue_mock:
            self.queue_manager._on_generator_recording_summary_completed(record_id, "Title")

        enqueue_mock.assert_called_once()
        args = enqueue_mock.call_args.args
        self.assertEqual(args[0], record_id)
        self.assertEqual(args[2], "")
        self.assertEqual(args[3], "Title")

    def test_daily_summary_completed_recording_skips_task_enqueue_when_tasks_exist(self):
        record_id = self.db.save("test.wav", "Transcription", 10.0, "Title")
        self.db.save_task(record_id=record_id, content="Existing task", is_ai_generated=True)

        with patch.object(self.queue_manager, "enqueue_task_extraction") as enqueue_mock:
            self.queue_manager._on_generator_recording_summary_completed(record_id, "Title")

        enqueue_mock.assert_called_once()
        # Central manager still receives the request, and decides to skip due to existing tasks.
        self.assertEqual(enqueue_mock.call_args.args[0], record_id)

    def test_task_extraction_does_not_skip_when_only_manual_tasks_exist(self):
        record_id = self.db.save("test.wav", "Transcription", 10.0, "Title")
        self.db.save_task(record_id=record_id, content="Manual task", tags="tag1", is_ai_generated=False)

        with patch('src.ui.summary_task_queue.AIAssistant') as MockAI:
            result = self.queue_manager.enqueue_task_extraction(record_id, "Transcription", "tag1", "Title")

        self.assertTrue(result)
        MockAI.assert_called_once()

    def test_session_history_records_queue_events(self):
        with patch('src.ui.summary_task_queue.AIAssistant'):
            self.queue_manager.enqueue_recording_summary(1, "text 1", "title 1")
            history = self.queue_manager.get_session_history()
            events = [entry.get("event") for entry in history]
            self.assertIn("queued", events)
            self.assertIn("started", events)

    def test_runtime_stats_counts_history_and_live_state(self):
        self.queue_manager._queue.append({"type": "summary"})
        self.queue_manager._current_task = {"type": "transcription", "record_id": 10}
        self.queue_manager._append_history("queued", {"type": "summary"})
        self.queue_manager._append_history("finished", {"type": "summary"})
        self.queue_manager._append_history("failed", {"type": "summary"}, "boom")
        self.queue_manager._append_history("skipped", {"type": "transcription"}, "dup")

        stats = self.queue_manager.get_runtime_stats()

        self.assertEqual(stats["running"], 1)
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["queued"], 1)
        self.assertEqual(stats["finished"], 1)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["skipped"], 1)

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

    def test_transcription_fatal_error_is_marked_skipped(self):
        self.queue_manager._current_task = {
            "type": "transcription",
            "record_id": 77,
            "title": "Recording 77",
        }
        skipped = []
        failed = []
        self.queue_manager.task_skipped.connect(lambda task, reason: skipped.append((task, reason)))
        self.queue_manager.task_failed.connect(lambda task, reason: failed.append((task, reason)))

        self.queue_manager._on_worker_error("Transcription subprocess timed out.")

        self.assertEqual(len(skipped), 1)
        self.assertEqual(len(failed), 0)
        self.assertEqual(skipped[0][0]["type"], "transcription")
        self.assertIn("timed out", skipped[0][1].lower())
        history = self.queue_manager.get_session_history()
        self.assertEqual(history[0]["event"], "skipped")

    def test_non_fatal_error_still_emits_failed(self):
        self.queue_manager._current_task = {
            "type": "transcription",
            "record_id": 77,
            "title": "Recording 77",
        }
        skipped = []
        failed = []
        self.queue_manager.task_skipped.connect(lambda task, reason: skipped.append((task, reason)))
        self.queue_manager.task_failed.connect(lambda task, reason: failed.append((task, reason)))

        self.queue_manager._on_worker_error("Some other error")

        self.assertEqual(len(skipped), 0)
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0][0]["type"], "transcription")
        history = self.queue_manager.get_session_history()
        self.assertEqual(history[0]["event"], "failed")

    def test_enqueue_rag_reindex_deduplicates_by_scope(self):
        with patch.object(self.queue_manager, "_start_next_if_idle"):
            self.assertTrue(self.queue_manager.enqueue_rag_reindex(scope="all"))
            self.assertTrue(self.queue_manager.enqueue_rag_reindex(scope="missing"))
            self.assertFalse(self.queue_manager.enqueue_rag_reindex(scope="missing"))

            queued = self.queue_manager.get_queue_list()
            self.assertEqual(len(queued), 2)
            scopes = sorted([q.get("reindex_scope") for q in queued])
            self.assertEqual(scopes, ["all", "missing"])

    def test_transcription_completion_persists_model_name(self):
        record_id = self.db.save("test.wav", "", 10.0, "Title")
        self.queue_manager._current_task = {
            "type": "transcription",
            "record_id": record_id,
            "title": "Title",
        }

        with patch.object(self.queue_manager, "enqueue_recording_summary") as enqueue_summary:
            self.queue_manager._on_worker_completed(
                {
                    "text": "recognized text",
                    "model_name": "sherpa-onnx",
                    "is_diarized": False,
                }
            )

        record = self.db.fetch_record(record_id)
        self.assertEqual(record["transcription"], "recognized text")
        self.assertEqual(record["transcription_model"], "sherpa-onnx")
        enqueue_summary.assert_called_once()

    def test_transcription_completion_batch_process_does_not_chain_summary(self):
        record_id = self.db.save("test.wav", "", 10.0, "Title")
        self.queue_manager._current_task = {
            "type": "transcription",
            "record_id": record_id,
            "title": "Title",
            "source": "batch_process",
        }

        with patch.object(self.queue_manager, "enqueue_recording_summary") as enqueue_summary:
            self.queue_manager._on_worker_completed(
                {
                    "text": "recognized text",
                    "model_name": "base",
                    "is_diarized": True,
                }
            )

        record = self.db.fetch_record(record_id)
        self.assertEqual(record["transcription"], "recognized text")
        self.assertEqual(record["transcription_model"], "base")
        enqueue_summary.assert_not_called()

if __name__ == '__main__':
    unittest.main()
