
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication

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

    def setUp(self):
        self.db_patcher = patch('src.ui.recording_widget.DBManager')
        self.mock_db = self.db_patcher.start().return_value
        self.mock_db.fetch_all.return_value = []
        self.mock_db.get_all_tags.return_value = []
        
        self.recorder_patcher = patch('src.ui.recording_widget.Recorder')
        self.recorder_patcher.start()
        
        self.rag_patcher = patch('src.rag_engine.RAGEngine')
        self.rag_patcher.start()

        # Instantiate widget (no record loaded initially)
        self.widget = RecordingWidget(MagicMock())

    def tearDown(self):
        self.widget.deleteLater()
        self.db_patcher.stop()
        self.recorder_patcher.stop()
        self.rag_patcher.stop()

    def test_clean_tab_removed(self):
        # Verify that "Cleaned" tab is NOT present
        # Tabs are: Original (0), Summary (1)
        self.assertEqual(self.widget.tabs.count(), 2)
        self.assertEqual(self.widget.tabs.tabText(0), "Original")
        self.assertEqual(self.widget.tabs.tabText(1), "Summary")

    def test_clean_button_removed(self):
        # Verify clean_btn attribute does not exist
        self.assertFalse(hasattr(self.widget, 'clean_btn'))
        
        # Verify AI actions layout only has Summarize button
        # We need to find the summarize button and check its parent layout
        # Or just checking attribute absence is enough for now given the implementation
        self.assertTrue(hasattr(self.widget, 'summarize_btn'))

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
            'cleaned_text': 'Should be ignored', 
            'summary': 'Summary', 
            'created_at': '2023-01-01', 
            'duration': 10.0
        }
        self.mock_db.fetch_all.return_value = [record]
        
        # This calls load_record internally
        self.widget.load_record(1)
        
        # Check that loaded text is correct
        self.assertEqual(self.widget.text_display.toPlainText(), 'test')
        self.assertEqual(self.widget.summary_display.toPlainText(), 'Summary')
        
        # Check that we didn't crash and tabs are still correct
        self.assertEqual(self.widget.tabs.count(), 2)

if __name__ == '__main__':
    unittest.main()
