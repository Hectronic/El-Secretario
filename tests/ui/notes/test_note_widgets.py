import os
import sys
import unittest

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.database import DBManager
from src.summary_generator import SummaryGenerator
from src.ui.note_widget import NoteWidget
from src.ui.welcome_widget import WelcomeWidget

app = QApplication.instance() or QApplication(sys.argv)


class TestNoteWidgets(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_notes_db.sqlite"
        self.db = DBManager(self.db_name)

    def tearDown(self):
        if os.path.exists(self.db_name):
            os.remove(self.db_name)

    def test_note_widget_save(self):
        """Test saving a note from the NoteWidget."""
        widget = NoteWidget(rag_engine=None, persistence=self.db)
        widget.title_input.setText('Widget Note')
        widget.content_editor.setPlainText('Widget Content')
        widget.tags_input.setText('widget_tag')
        QTest.mouseClick(widget.save_btn, Qt.MouseButton.LeftButton)
        all_records = self.db.fetch_all()
        self.assertEqual(len(all_records), 1)
        self.assertEqual(all_records[0]['title'], 'Widget Note')
        self.assertEqual(all_records[0]['type'], 'note')

    def test_note_widget_uses_injected_persistence(self):
        widget = NoteWidget(rag_engine=None, persistence=self.db)
        try:
            self.assertIs(widget.db, self.db)
        finally:
            widget.deleteLater()

    def test_welcome_widget_new_note_signal(self):
        """Test that WelcomeWidget emits new_note_requested signal."""
        widget = WelcomeWidget(self.db)
        signal_received = False

        def on_new_note():
            nonlocal signal_received
            signal_received = True
        widget.new_note_requested.connect(on_new_note)
        QTest.mouseClick(widget.new_note_top_btn, Qt.MouseButton.LeftButton)
        self.assertTrue(signal_received)

    def test_summary_generator_includes_notes(self):
        """Test that SummaryGenerator includes notes in daily summaries."""
        from datetime import date
        today = date.today().isoformat()
        self.db.save_note('Note Title', 'Note Content')
        self.db.save('rec.wav', 'Rec Content', 10.0, 'Rec Title')
        generator = SummaryGenerator(generate_daily=True, generate_weekly=False, generate_recordings=False)
        generator.db = self.db
        dates = self.db.get_dates_with_content()
        self.assertIn(today, dates)
        records = self.db.fetch_by_dates([today])
        self.assertEqual(len(records), 2)
        types = [r['type'] for r in records]
        self.assertIn('note', types)
        self.assertIn('recording', types)
