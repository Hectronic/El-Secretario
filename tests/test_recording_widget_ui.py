
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from PyQt6 import sip

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.recording_widget import RecordingWidget

class TestRecordingWidgetUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
        cls.app.setQuitOnLastWindowClosed(False)

    @classmethod
    def tearDownClass(cls):
        if QApplication.instance():
            QApplication.instance().processEvents()
            QApplication.instance().setQuitOnLastWindowClosed(True)

    def setUp(self):
        self.db_patcher = patch('src.ui.recording_widget.DBManager')
        self.mock_db = self.db_patcher.start().return_value
        self.mock_db.fetch_all.return_value = []
        self.mock_db.get_all_tags.return_value = []

        self.media_player_patcher = patch('src.ui.recording_widget.QMediaPlayer')
        self.audio_output_patcher = patch('src.ui.recording_widget.QAudioOutput')
        self.media_player_patcher.start()
        self.audio_output_patcher.start()
        
        self.recorder_patcher = patch('src.ui.recording_widget.Recorder')
        self.recorder_patcher.start()
        
        self.rag_patcher = patch('src.rag_engine.RAGEngine')
        self.rag_patcher.start()

        # Instantiate widget (no record loaded initially)
        self.widget = RecordingWidget(MagicMock())

    def tearDown(self):
        self.widget.close()
        sip.delete(self.widget)
        if QApplication.instance():
            QApplication.instance().processEvents()
        self.db_patcher.stop()
        self.media_player_patcher.stop()
        self.audio_output_patcher.stop()
        self.recorder_patcher.stop()
        self.rag_patcher.stop()

    def test_clean_tab_removed(self):
        # Verify that "Cleaned" tab is NOT present
        # Tabs are: Original (0), Notes (1), Summary (2), Tasks (3)
        self.assertEqual(self.widget.tabs.count(), 4)
        self.assertEqual(self.widget.tabs.tabText(0), "Original")
        self.assertEqual(self.widget.tabs.tabText(1), "Notes")
        self.assertEqual(self.widget.tabs.tabText(2), "Summary")
        self.assertEqual(self.widget.tabs.tabText(3), "Tasks")

    def test_clean_button_removed(self):
        # Verify clean_btn attribute does not exist
        self.assertFalse(hasattr(self.widget, 'clean_btn'))
        
        # Verify AI actions layout only has Summarize button
        # We need to find the summarize button and check its parent layout
        # Or just checking attribute absence is enough for now given the implementation
        self.assertTrue(hasattr(self.widget, 'summarize_btn'))

    def test_transcription_model_combo_includes_sherpa_onnx(self):
        options = [self.widget.model_combo.itemText(i) for i in range(self.widget.model_combo.count())]
        self.assertIn("sherpa-onnx", options)

    def test_start_transcription_shows_error_without_starting_thread_when_sherpa_model_missing(self):
        self.widget.model_combo.setCurrentText("sherpa-onnx")
        fake_settings = MagicMock(spec=QSettings)
        fake_settings.value.side_effect = lambda key, default=None, type=None: {
            "hf_token": "",
            "force_cpu": False,
            "compute_type": "auto",
            "transcription_backend": "auto",
            "sherpa_onnx_model_dir": "/tmp/missing-sherpa-model",
            "sherpa_onnx_auto_download": False,
        }.get(key, default)

        with patch("src.ui.recording_widget.QSettings", return_value=fake_settings), \
             patch("src.ui.recording_widget.TranscriberThread") as mock_thread, \
             patch("src.ui.recording_widget.QMessageBox.critical") as critical_mock:
            self.widget.start_transcription("/tmp/fake.wav")

        mock_thread.assert_not_called()
        critical_mock.assert_called_once()
        self.assertIn("does not exist", critical_mock.call_args.args[2])

    def test_load_record_does_not_fail(self):
        # Ensure loading a record doesn't crash due to missing cleaned_text logic
        record = {
            'id': 1, 
            'filename': 'test.wav', 
            'transcription': 'test', 
            'is_diarized': 0, 
            'transcription_model': 'base', 
            'title': 'Test', 
            'tags': '', 
            'recording_notes': 'Important context',
            'cleaned_text': 'Should be ignored', 
            'summary': 'Summary', 
            'created_at': '2023-01-01', 
            'duration': 10.0
        }
        self.mock_db.fetch_all.return_value = [record]
        self.mock_db.fetch_record.return_value = record
        self.mock_db.get_tasks_by_record.return_value = []
        
        # This calls load_record internally
        self.widget.load_record(1)
        
        # Check that loaded text is correct
        self.assertEqual(self.widget.text_display.toPlainText(), 'test')
        self.assertEqual(self.widget.notes_display.toPlainText(), 'Important context')
        self.assertEqual(self.widget.summary_display.toPlainText(), 'Summary')
        
        # Check that we didn't crash and tabs are still correct
        self.assertEqual(self.widget.tabs.count(), 4)

    def test_auto_summary_without_queue_shows_warning(self):
        self.widget.current_record_id = 1
        self.widget.current_recording_path = "/tmp/test.wav"
        self.widget.auto_summarize_after_transcription = True
        self.mock_db.fetch_record.return_value = {
            'id': 1,
            'filename': 'test.wav',
            'transcription': 'old',
            'is_diarized': 0,
            'transcription_model': 'base',
            'title': 'Test',
            'tags': '',
            'recording_notes': '',
            'summary': '',
            'created_at': '2023-01-01',
            'duration': 10.0
        }
        self.mock_db.get_tasks_by_record.return_value = []

        result = {
            "text": "new transcription",
            "model_name": "base",
            "audio_duration": 5.0,
            "audio_size_bytes": 1024,
            "transcription_time": 0.5,
            "is_diarized": False,
        }

        with patch('src.ui.recording_widget.QMessageBox.warning') as warning_mock:
            self.widget.on_transcription_finished(result)
            warning_mock.assert_called_once()

    def test_auto_summary_mode_enqueues_only_summary_in_queue(self):
        queue = MagicMock()
        self.widget.summary_task_queue = queue
        self.widget.current_record_id = 1
        self.widget.current_recording_path = "/tmp/test.wav"
        self.widget.auto_summarize_after_transcription = True
        self.widget.title_input.setText("Test recording")
        self.widget.tags_input.setText("alpha, beta")
        self.mock_db.fetch_record.return_value = {
            'id': 1,
            'filename': 'test.wav',
            'transcription': 'old',
            'is_diarized': 0,
            'transcription_model': 'base',
            'title': 'Test',
            'tags': 'alpha, beta',
            'recording_notes': '',
            'summary': '',
            'created_at': '2023-01-01',
            'duration': 10.0
        }
        self.mock_db.get_tasks_by_record.return_value = []

        result = {
            "text": "new transcription",
            "model_name": "base",
            "audio_duration": 5.0,
            "audio_size_bytes": 1024,
            "transcription_time": 0.5,
            "is_diarized": False,
        }

        self.widget.on_transcription_finished(result)
        queue.enqueue_recording_summary.assert_called_once()
        queue.enqueue_task_extraction.assert_not_called()

    def test_extract_button_switches_to_reextract_when_ai_tasks_exist(self):
        self.widget.current_record_id = 7
        self.mock_db.has_ai_tasks_for_record.return_value = True

        self.widget._update_extract_tasks_button()

        self.assertEqual(self.widget.extract_tasks_btn.text(), "Re-extract Tasks (AI)")

    def test_reextract_deletes_ai_tasks_and_forces_queue_request(self):
        queue = MagicMock()
        self.widget.summary_task_queue = queue
        self.widget.current_record_id = 7
        self.widget.title_input.setText("Weekly sync")
        self.widget.tags_input.setText("ops")
        self.widget.text_display.setText("Transcript")
        self.widget.notes_display.setText("")
        self.mock_db.compose_ai_text.return_value = "Transcript"
        self.mock_db.has_ai_tasks_for_record.return_value = True

        self.widget.run_ai_task("task_extraction")

        self.mock_db.delete_ai_tasks_by_record.assert_called_once_with(7)
        queue.enqueue_task_extraction.assert_called_once_with(7, "Transcript", "ops", "Weekly sync", force=True)

    def test_refresh_from_background_queue_updates_summary_and_tasks(self):
        self.widget.current_record_id = 7
        self.mock_db.fetch_record.return_value = {
            "id": 7,
            "summary": "Queue summary result"
        }
        self.mock_db.get_tasks_by_record.return_value = []

        with patch.object(self.widget.tasks_widget, "refresh") as mock_tasks_refresh:
            self.widget.refresh_from_background_queue(include_summary=True, include_tasks=True)

        self.assertEqual(self.widget.summary_display.toPlainText(), "Queue summary result")
        mock_tasks_refresh.assert_called_once()

    def test_open_chat_for_recording_emits_only_recording_context(self):
        self.widget.current_record_id = 11
        self.mock_db.fetch_record.return_value = {
            "id": 11,
            "title": "Weekly sync",
            "created_at": "2026-03-09 10:00:00",
            "tags": "ops,team",
        }
        emitted = []
        self.widget.start_chat_requested.connect(lambda ctx: emitted.append(ctx))

        self.widget.open_chat_for_recording()

        self.assertEqual(len(emitted), 1)
        self.assertEqual(
            emitted[0],
            [{"type": "recording", "value": 11, "label": "Weekly sync"}],
        )

if __name__ == '__main__':
    unittest.main()
