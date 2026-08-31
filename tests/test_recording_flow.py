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
import wave
import tempfile
import shutil
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSettings

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.main_window import MainWindow
from src.ui.audio_editor.widget import AudioEditorWidget
from src.ui.recording_in_progress_widget import RecordingInProgressWidget
from src.ui.recording_widget import RecordingWidget

class TestRecordingFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
        cls._qsettings_dir = tempfile.mkdtemp(prefix="secretario_qsettings_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            cls._qsettings_dir,
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_qsettings_dir") and os.path.isdir(cls._qsettings_dir):
            shutil.rmtree(cls._qsettings_dir, ignore_errors=True)

    def setUp(self):
        # Patch Recorder
        self.recorder_patcher = patch('src.ui.main_window.Recorder')
        self.mock_recorder_cls = self.recorder_patcher.start()
        self.mock_recorder = self.mock_recorder_cls.return_value
        self.mock_recorder.is_recording = False
        self.mock_recorder.is_paused = False
        self.mock_recorder.stop.return_value = None
        
        # Patch DBManager to avoid real DB ops
        self.db_patcher = patch('src.ui.main_window.DBManager')
        self.mock_db_cls = self.db_patcher.start()
        self.mock_db = self.mock_db_cls.return_value
        self.mock_db.fetch_all.return_value = []
        self.mock_db.save.return_value = 123 # Mock ID
        self.mock_db.get_all_tags.return_value = []
        self.mock_db.fetch_record.return_value = {
            'id': 123, 'title': 'Test', 'transcription': 'test', 'tags': 'test',
            'summary': '', 'created_at': '2023-01-01', 'file_path': 'foo.wav', 'filename': 'foo.wav', 'type': 'recording', 'is_diarized': False, 'duration': 0.0
        }
        
        # Patch DBManager for recording_in_progress_widget (for TagsLineEdit)
        self.db_patcher2 = patch('src.ui.recording_in_progress_widget.DBManager')
        self.mock_db2 = self.db_patcher2.start().return_value
        self.mock_db2.get_all_tags.return_value = []
        
        # Patch RAGEngine
        # Since MainWindow imports it inside __init__, we need to patch where it comes from
        self.rag_patcher = patch('src.rag_engine.RAGEngine')
        self.rag_patcher.start()
        
        # Patch DBManager for recording_widget (for TagsLineEdit)
        self.db_patcher3 = patch('src.ui.recording_widget.DBManager')
        self.mock_db3 = self.db_patcher3.start().return_value
        self.mock_db3.get_all_tags.return_value = []
        self.mock_db3.fetch_all.return_value = []
        self.mock_db3.fetch_record.return_value = {
            'id': 123, 'title': 'Test', 'transcription': 'test', 'tags': 'test',
            'summary': '', 'created_at': '2023-01-01', 'file_path': 'foo.wav', 'filename': 'foo.wav', 'type': 'recording', 'is_diarized': False, 'duration': 0.0
        }
        self.mock_db3.get_tasks_by_record.return_value = []

        # Patch DBManager for the dedicated audio editor tab.
        self.db_patcher4 = patch('src.ui.audio_editor.widget.DBManager')
        self.mock_db4 = self.db_patcher4.start().return_value
        self.mock_db4.get_all_tags.return_value = []
        self.mock_db4.fetch_all.return_value = []
        self.mock_db4.fetch_record.return_value = self.mock_db3.fetch_record.return_value
        self.mock_db4.get_tasks_by_record.return_value = []

        # Avoid real multimedia backend usage in headless CI.
        self.media_player_patcher = patch('src.ui.recording_widget.QMediaPlayer')
        self.audio_output_patcher = patch('src.ui.recording_widget.QAudioOutput')
        self.media_player_patcher.start()
        self.audio_output_patcher.start()

        # Keep this test focused on UI flow, not on actual transcription execution.
        self.start_transcription_patcher = patch.object(
            RecordingWidget,
            'start_transcription_with_config',
            autospec=True
        )
        self.mock_start_transcription = self.start_transcription_patcher.start()

        self.msgbox_patcher = patch('src.ui.main_window.recording_tabs.QMessageBox.critical')
        self.mock_msgbox = self.msgbox_patcher.start()

        self.window = MainWindow()

        # Create a dummy WAV file
        self.dummy_wav_path = os.path.join(tempfile.gettempdir(), "test_audio.wav")
        with wave.open(self.dummy_wav_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(b'\x00' * 1024)
        self.mock_recorder.stop.return_value = self.dummy_wav_path

    def tearDown(self):
        if os.path.exists(self.dummy_wav_path):
            os.remove(self.dummy_wav_path)
        self.window.close()
        self.recorder_patcher.stop()
        self.db_patcher.stop()
        self.db_patcher2.stop()
        self.db_patcher3.stop()
        self.db_patcher4.stop()
        self.media_player_patcher.stop()
        self.audio_output_patcher.stop()
        self.start_transcription_patcher.stop()
        self.rag_patcher.stop()
        self.msgbox_patcher.stop()

    def test_new_recording_flow(self):
        # 1. Open New Recording Tab
        # Use start_new_recording with a dummy config
        self.window.start_new_recording({})
        
        # Verify RecordingInProgressWidget is open
        current_widget = self.window.central_tabs.currentWidget()
        self.assertIsInstance(current_widget, RecordingInProgressWidget)
        self.assertEqual(self.window.central_tabs.tabText(self.window.central_tabs.currentIndex()), "Recording...")
        
        # Verify Recorder started
        self.mock_recorder.start.assert_called()
        
        # 2. Simulate Finish
        # We can click the button or call the method directly
        current_widget.finish_recording()
        
        if self.mock_msgbox.called:
            print("MessageBox was called:", self.mock_msgbox.call_args)

    def test_auto_summary_option_propagates_and_is_saved_from_recording_tab(self):
        settings = QSettings("Hectronic", "Secretario")
        prev_value = settings.value("rec_config/auto_summarize_after_transcription", None)
        settings.setValue("rec_config/auto_summarize_after_transcription", False)
        settings.sync()

        try:
            self.window.start_new_recording({})
            current_widget = self.window.central_tabs.currentWidget()
            self.assertIsInstance(current_widget, RecordingInProgressWidget)

            current_widget.auto_summary_check.setChecked(True)
            current_widget.finish_recording()

            new_widget = self.window.central_tabs.currentWidget()
            self.assertIsInstance(new_widget, RecordingWidget)
            self.assertTrue(new_widget.auto_summarize_after_transcription)

            self.assertTrue(self.mock_start_transcription.called)
            _, args, _ = self.mock_start_transcription.mock_calls[-1]
            passed_config = args[2]
            self.assertTrue(passed_config.get("auto_summarize_after_transcription"))
        finally:
            if prev_value is None:
                settings.remove("rec_config/auto_summarize_after_transcription")
            else:
                settings.setValue("rec_config/auto_summarize_after_transcription", prev_value)
            settings.sync()
        
        # Verify Recorder stopped
        self.mock_recorder.stop.assert_called()
        
        # Verify transition to RecordingWidget
        new_widget = self.window.central_tabs.currentWidget()
        self.assertIsInstance(new_widget, RecordingWidget)
        self.assertEqual(new_widget.current_record_id, 123)
        
        # Verify transcription started
        # We need to mock start_transcription on RecordingWidget or check if it was called.
        # Since RecordingWidget is instantiated inside on_recording_finished, we can't easily mock it beforehand 
        # unless we patch RecordingWidget class.
        # But we can check if the widget state implies transcription started (e.g. progress bar visible).
        # Or we can just trust the integration if no error occurred.
        
        # Let's check if DB save was called
        self.mock_db.save.assert_called()
        self.assertTrue(self.mock_start_transcription.called)
        
        if self.mock_msgbox.called:
            print("MessageBox was called:", self.mock_msgbox.call_args)

    def test_open_recording_tab_can_create_duplicate_editor_instance(self):
        self.window.central_tabs.clear()
        first_widget = self.window.open_recording_tab(123)
        second_widget = self.window.open_recording_tab(123, force_new=True)

        self.assertIsNot(first_widget, second_widget)
        self.assertEqual(first_widget.current_record_id, 123)
        self.assertEqual(second_widget.current_record_id, 123)
        self.assertEqual(self.window.central_tabs.count(), 2)
        self.assertEqual(self.window.central_tabs.widget(0), first_widget)
        self.assertEqual(self.window.central_tabs.widget(1), second_widget)

    def test_open_recording_editor_tab_opens_audio_edit_mode(self):
        self.window.central_tabs.clear()
        editor_widget = self.window.open_recording_editor_tab(123)

        self.assertIsInstance(editor_widget, AudioEditorWidget)
        self.assertEqual(editor_widget.current_record_id, 123)
        self.assertEqual(self.window.central_tabs.count(), 1)
        self.assertEqual(self.window.central_tabs.widget(0), editor_widget)
        self.assertIn("Editor", self.window.central_tabs.tabText(0))

if __name__ == '__main__':
    unittest.main()
