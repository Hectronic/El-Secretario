
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import tempfile
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from PyQt6 import sip
import numpy as np
import soundfile as sf

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

    def test_main_widget_does_not_expose_trim_controls(self):
        self.assertIsNone(self.widget.trim_start_spin)
        self.assertIsNone(self.widget.trim_end_spin)
        self.assertIsNone(self.widget.mark_start_btn)
        self.assertIsNone(self.widget.mark_end_btn)
        self.assertIsNone(self.widget.trim_btn)
        self.assertTrue(hasattr(self.widget, "edit_audio_btn"))
        self.assertFalse(self.widget.edit_audio_btn.isEnabled())

    def test_audio_editor_mode_is_minimal(self):
        editor_widget = RecordingWidget(MagicMock(), audio_edit_mode=True)
        try:
            self.assertTrue(editor_widget.audio_edit_mode)
            self.assertIsNone(getattr(editor_widget, "tabs", None))
            self.assertIsNone(getattr(editor_widget, "model_combo", None))
            self.assertIsNone(getattr(editor_widget, "title_input", None))
            self.assertTrue(hasattr(editor_widget, "trim_start_spin"))
            self.assertTrue(hasattr(editor_widget, "trim_end_spin"))
            self.assertTrue(hasattr(editor_widget, "trim_btn"))
            self.assertFalse(hasattr(editor_widget, "edit_audio_btn"))
        finally:
            editor_widget.close()
            sip.delete(editor_widget)

    def test_transcription_model_combo_includes_sherpa_onnx(self):
        options = [self.widget.model_combo.itemText(i) for i in range(self.widget.model_combo.count())]
        self.assertIn("Sherpa-ONNX (Local)", options)

    def test_retranscribe_button_is_integrated_with_transcription_controls(self):
        self.assertIsNotNone(self.widget.retranscribe_btn)
        self.assertEqual(self.widget.retranscribe_btn.text(), "Retranscribe")
        self.assertEqual(self.widget.retranscribe_btn.minimumHeight(), 34)
        self.assertEqual(self.widget.retranscribe_btn.property("class"), "calendar-primary-btn")
        self.assertFalse(self.widget.retranscribe_btn.isEnabled())

    def test_bottom_actions_keep_ai_buttons_without_retranscribe_duplication(self):
        self.assertEqual(self.widget.summarize_btn.text(), "Summarize (AI)")
        self.assertEqual(self.widget.extract_tasks_btn.text(), "Extract Tasks (AI)")
        self.assertNotEqual(self.widget.summarize_btn, self.widget.retranscribe_btn)
        self.assertNotEqual(self.widget.extract_tasks_btn, self.widget.retranscribe_btn)

    def test_recording_action_buttons_use_consistent_style_classes(self):
        expected = {
            self.widget.retranscribe_btn: ("calendar-primary-btn", 34),
            self.widget.edit_audio_btn: ("calendar-primary-btn", 38),
            self.widget.summarize_btn: ("calendar-nav-btn", 36),
            self.widget.extract_tasks_btn: ("calendar-nav-btn", 36),
            self.widget.save_all_btn: ("calendar-primary-btn", 36),
            self.widget.ask_meeting_btn: ("calendar-primary-btn", 38),
            self.widget.delete_btn: ("record-del-btn", 38),
            self.widget.copy_transcription_btn: ("calendar-nav-btn", None),
        }

        for button, (style_class, min_height) in expected.items():
            with self.subTest(button=button.text()):
                self.assertEqual(button.property("class"), style_class)
                if min_height is not None:
                    self.assertEqual(button.minimumHeight(), min_height)

    def test_save_button_is_bottom_primary_action_and_tracks_dirty_state(self):
        self.assertEqual(self.widget.save_all_btn.text(), "Save All Changes")
        self.assertEqual(self.widget.save_all_btn.property("class"), "calendar-primary-btn")
        self.assertFalse(self.widget.save_all_btn.isEnabled())

        bottom_layout = self.widget.layout().itemAt(self.widget.layout().count() - 1).layout()
        bottom_widgets = [
            bottom_layout.itemAt(i).widget()
            for i in range(bottom_layout.count())
            if bottom_layout.itemAt(i).widget() is not None
        ]
        self.assertIn(self.widget.save_all_btn, bottom_widgets)

        self.widget.title_input.setText("Changed title")
        self.assertTrue(self.widget.save_all_btn.isEnabled())

        self.widget._set_dirty(False)
        self.assertFalse(self.widget.save_all_btn.isEnabled())

    def test_copy_transcription_button_copies_full_text_without_selection(self):
        self.assertEqual(self.widget.copy_transcription_btn.text(), "Copy Transcription")
        self.assertFalse(self.widget.copy_transcription_btn.isEnabled())

        clipboard = QApplication.clipboard()
        clipboard.clear()
        emitted_statuses = []
        self.widget.status_changed.connect(emitted_statuses.append)
        transcription = "First paragraph.\n\nSecond paragraph."

        self.widget.text_display.setPlainText(transcription)
        self.assertTrue(self.widget.copy_transcription_btn.isEnabled())
        self.widget.copy_transcription_btn.click()

        self.assertEqual(clipboard.text(), transcription)
        self.assertEqual(emitted_statuses[-1], "Transcription copied.")

    def test_copy_transcription_button_ignores_notes_only_records(self):
        record = {
            'id': 1,
            'filename': 'test.wav',
            'transcription': '',
            'is_diarized': 0,
            'transcription_model': 'base',
            'title': 'Test',
            'tags': '',
            'recording_notes': 'Only notes',
            'summary': '',
            'created_at': '2023-01-01',
            'duration': 10.0,
        }
        self.mock_db.fetch_record.return_value = record
        self.mock_db.get_tasks_by_record.return_value = []

        self.widget.load_record(1)

        self.assertFalse(self.widget.copy_transcription_btn.isEnabled())
        self.assertTrue(self.widget.summarize_btn.isEnabled())

    def test_start_transcription_shows_error_without_starting_thread_when_sherpa_model_missing(self):
        self.widget.model_combo.setCurrentText("Sherpa-ONNX (Local)")
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
        self.assertFalse(self.widget.save_all_btn.isEnabled())
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
        queue.enqueue_task_extraction.assert_called_once_with(
            7,
            "Transcript",
            "ops",
            "Weekly sync",
            force=True,
            source="recording",
        )

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

    def test_trim_audio_selection_updates_duration_and_retranscribes(self):
        tempdir = tempfile.mkdtemp(prefix="secretario_widget_trim_")
        recordings_dir = os.path.join(tempdir, "recordings")
        os.makedirs(recordings_dir, exist_ok=True)
        audio_path = os.path.join(recordings_dir, "trim.wav")
        tone = np.sin(2 * np.pi * 220 * np.arange(16000) / 16000).astype(np.float32)
        sf.write(audio_path, tone, 16000)

        self.mock_db.fetch_record.return_value = {
            "id": 42,
            "filename": "trim.wav",
            "transcription": "old text",
            "recording_notes": "",
            "summary": "",
            "title": "Trim test",
            "tags": "",
            "is_diarized": 0,
            "created_at": "2026-04-16 10:00:00",
            "duration": 1.0,
            "type": "recording",
        }
        self.mock_db.get_tasks_by_record.return_value = []

        editor_widget = RecordingWidget(MagicMock(), audio_edit_mode=True)
        try:
            editor_widget.db = self.mock_db
            editor_widget.rag = MagicMock()

            with patch("src.ui.recording_widget.os.getcwd", return_value=tempdir), \
                 patch.object(editor_widget, "start_transcription") as mock_start_transcription, \
                 patch("src.ui.recording_widget.QMessageBox.warning") as warning_mock, \
                 patch("src.ui.recording_widget.QMessageBox.critical") as critical_mock:
                editor_widget.load_record(42)
                editor_widget.trim_start_spin.setValue(0.25)
                editor_widget.trim_end_spin.setValue(0.75)
                editor_widget.trim_audio_selection()

            info = sf.info(audio_path)
            self.assertAlmostEqual(info.frames / info.samplerate, 0.5, places=2)
            self.mock_db.update_duration.assert_called_with(42, unittest.mock.ANY)
            mock_start_transcription.assert_called_once_with(audio_path)
            warning_mock.assert_not_called()
            critical_mock.assert_not_called()
        finally:
            editor_widget.close()
            sip.delete(editor_widget)

        backup_path = f"{audio_path}.orig"
        self.assertTrue(os.path.exists(backup_path))
        try:
            os.remove(audio_path)
            os.remove(backup_path)
            os.rmdir(tempdir)
        except OSError:
            pass

if __name__ == '__main__':
    unittest.main()
