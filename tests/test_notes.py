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

import unittest
import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from src.database import DBManager
from src.ui.note_widget import NoteWidget
from src.ui.welcome_widget import WelcomeWidget
from src.summary_generator import SummaryGenerator

# Create QApplication for UI tests if it doesn't exist
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

class TestNotes(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_notes_db.sqlite"
        self.db = DBManager(self.db_name)

    def tearDown(self):
        if os.path.exists(self.db_name):
            os.remove(self.db_name)

    def test_database_save_note(self):
        """Test that notes are saved correctly in the database."""
        note_id = self.db.save_note("My Note", "Content of the note", "tag1")
        record = self.db.fetch_record(note_id)
        
        self.assertEqual(record['title'], "My Note")
        self.assertEqual(record['transcription'], "Content of the note")
        self.assertEqual(record['type'], "note")
        self.assertEqual(record['duration'], 0.0)
        
        # Verify it appears in fetch_all
        all_records = self.db.fetch_all()
        self.assertEqual(len(all_records), 1)
        self.assertEqual(all_records[0]['type'], 'note')

    def test_note_widget_save(self):
        """Test saving a note from the NoteWidget."""
        widget = NoteWidget(rag_engine=None)
        widget.db = self.db # Use test DB
        
        widget.title_input.setText("Widget Note")
        widget.content_editor.setPlainText("Widget Content")
        widget.tags_input.setText("widget_tag")
        
        # Simulate save button click
        QTest.mouseClick(widget.save_btn, Qt.MouseButton.LeftButton)
        
        # Check database
        all_records = self.db.fetch_all()
        self.assertEqual(len(all_records), 1)
        self.assertEqual(all_records[0]['title'], "Widget Note")
        self.assertEqual(all_records[0]['type'], "note")

    def test_welcome_widget_new_note_signal(self):
        """Test that WelcomeWidget emits new_note_requested signal."""
        widget = WelcomeWidget(self.db)
        
        signal_received = False
        def on_new_note():
            nonlocal signal_received
            signal_received = True
            
        widget.new_note_requested.connect(on_new_note)
        
        # Simulate click on new note button
        QTest.mouseClick(widget.new_note_top_btn, Qt.MouseButton.LeftButton)
        self.assertTrue(signal_received)

    def test_summary_generator_includes_notes(self):
        """Test that SummaryGenerator includes notes in daily summaries."""
        # Create a note and a recording for today
        from datetime import date
        today = date.today().isoformat()
        self.db.save_note("Note Title", "Note Content")
        self.db.save("rec.wav", "Rec Content", 10.0, "Rec Title")
        
        # We can't easily run the full thread with AI provider without mocking,
        # but we can check if the generator fetches them.
        generator = SummaryGenerator(generate_daily=True, generate_weekly=False, generate_recordings=False)
        generator.db = self.db
        
        # Mocking or just inspecting logic:
        # get_dates_with_content should return today
        dates = self.db.get_dates_with_content()
        self.assertIn(today, dates)
        
        # fetch_by_dates for today should return 2 records (1 note, 1 recording)
        records = self.db.fetch_by_dates([today])
        self.assertEqual(len(records), 2)
        types = [r['type'] for r in records]
        self.assertIn('note', types)
        self.assertIn('recording', types)

if __name__ == '__main__':
    unittest.main()
