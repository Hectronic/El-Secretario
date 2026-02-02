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

"""Tests for data export/import functionality."""

import os
import json
import unittest
from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.data_export import DataExporter, ImportStats, ImportResult


class TestDataExport(unittest.TestCase):
    """Test cases for the DataExporter class."""

    def setUp(self):
        """Set up test databases."""
        self.db_name = "test_export_db.sqlite"
        self.notebook_db_name = "test_export_notebooks.db"
        self.export_file = "test_export.json"
        
        self.db = DBManager(self.db_name)
        self.notebook_db = NotebookDBManager(self.notebook_db_name)
        self.exporter = DataExporter(self.db, self.notebook_db)

    def tearDown(self):
        """Clean up test files."""
        for f in [self.db_name, self.notebook_db_name, self.export_file]:
            if os.path.exists(f):
                os.remove(f)

    def test_export_records(self):
        """Test exporting records."""
        # Create sample data
        self.db.save("test1.wav", "Hello World", 10.5, "Test Title 1")
        self.db.save("test2.wav", "Goodbye World", 20.0, "Test Title 2")
        
        records = self.exporter.export_records()
        
        self.assertEqual(len(records), 2)
        # Check that records have content hashes
        self.assertIn('_content_hash', records[0])
        self.assertIn('_content_hash', records[1])

    def test_export_chat_sessions(self):
        """Test exporting chat sessions."""
        self.db.save_chat_session("Chat 1", "All", "[]")
        self.db.save_chat_session("Chat 2", "Work", "[{'role': 'user'}]")
        
        sessions = self.exporter.export_chat_sessions()
        
        self.assertEqual(len(sessions), 2)
        # Verify both sessions are exported (order may vary if created in same millisecond)
        names = {s['name'] for s in sessions}
        self.assertEqual(names, {"Chat 1", "Chat 2"})

    def test_export_notebooks(self):
        """Test exporting notebooks with entries."""
        nb_id = self.notebook_db.create_notebook("Test Notebook", "Description")
        self.notebook_db.add_text_entry(nb_id, "Entry content", "Entry title")
        self.notebook_db.add_text_entry(nb_id, "Second entry", "Entry 2")
        
        notebooks = self.exporter.export_notebooks()
        
        self.assertEqual(len(notebooks), 1)
        self.assertEqual(notebooks[0]['name'], "Test Notebook")
        self.assertEqual(len(notebooks[0]['entries']), 2)

    def test_export_all(self):
        """Test full export to JSON file."""
        # Create sample data
        self.db.save("test.wav", "Transcription", 10.0, "Recording 1")
        self.db.save_chat_session("Chat 1", "All", "[]")
        nb_id = self.notebook_db.create_notebook("Notebook 1")
        self.notebook_db.add_text_entry(nb_id, "Note content", "Note 1")
        
        stats = self.exporter.export_all(self.export_file)
        
        # Verify stats
        self.assertEqual(stats['records_count'], 1)
        self.assertEqual(stats['chat_sessions_count'], 1)
        self.assertEqual(stats['notebooks_count'], 1)
        
        # Verify file was created
        self.assertTrue(os.path.exists(self.export_file))
        
        # Verify file content
        with open(self.export_file, 'r') as f:
            data = json.load(f)
        
        self.assertIn('export_metadata', data)
        self.assertEqual(data['export_metadata']['app_name'], "El Secretario")
        self.assertEqual(len(data['records']), 1)
        self.assertEqual(len(data['chat_sessions']), 1)
        self.assertEqual(len(data['notebooks']), 1)


class TestDataImport(unittest.TestCase):
    """Test cases for data import functionality."""

    def setUp(self):
        """Set up test databases."""
        self.db_name = "test_import_db.sqlite"
        self.notebook_db_name = "test_import_notebooks.db"
        self.export_file = "test_import.json"
        
        self.db = DBManager(self.db_name)
        self.notebook_db = NotebookDBManager(self.notebook_db_name)
        self.exporter = DataExporter(self.db, self.notebook_db)

    def tearDown(self):
        """Clean up test files."""
        for f in [self.db_name, self.notebook_db_name, self.export_file]:
            if os.path.exists(f):
                os.remove(f)

    def test_import_records(self):
        """Test importing records."""
        records = [
            {
                'created_at': '2026-01-15 10:00:00',
                'filename': 'test.wav',
                'duration': 10.0,
                'transcription': 'Hello World',
                'title': 'Test Recording',
                'tags': 'test, import',
                '_content_hash': 'abc123'
            }
        ]
        
        stats = self.exporter.import_records(records)
        
        self.assertEqual(stats.imported, 1)
        self.assertEqual(stats.skipped, 0)
        
        # Verify data was imported
        all_records = self.db.fetch_all()
        self.assertEqual(len(all_records), 1)
        self.assertEqual(all_records[0]['title'], 'Test Recording')

    def test_import_duplicate_detection(self):
        """Test that duplicate records are detected and skipped."""
        # First, create a record
        self.db.save("test.wav", "Hello World", 10.0, "Test Recording")
        
        # Get the created_at timestamp
        existing = self.db.fetch_all()[0]
        
        # Now try to import a record with the same timestamp and content
        records = [
            {
                'created_at': existing['created_at'],
                'filename': 'test.wav',
                'duration': 10.0,
                'transcription': 'Hello World',  # Same content
                'title': 'Duplicate Recording',
            }
        ]
        
        stats = self.exporter.import_records(records)
        
        self.assertEqual(stats.imported, 0)
        self.assertEqual(stats.skipped, 1)
        
        # Verify no new record was added
        all_records = self.db.fetch_all()
        self.assertEqual(len(all_records), 1)

    def test_import_chat_sessions(self):
        """Test importing chat sessions."""
        sessions = [
            {
                'name': 'Imported Chat',
                'collection': 'All',
                'messages': '[{"role": "user", "content": "Hello"}]',
                'created_at': '2026-01-15 10:00:00',
            }
        ]
        
        stats = self.exporter.import_chat_sessions(sessions)
        
        self.assertEqual(stats.imported, 1)
        self.assertEqual(stats.skipped, 0)
        
        all_sessions = self.db.fetch_chat_sessions()
        self.assertEqual(len(all_sessions), 1)
        self.assertEqual(all_sessions[0]['name'], 'Imported Chat')

    def test_import_notebooks(self):
        """Test importing notebooks with entries."""
        notebooks = [
            {
                'name': 'Imported Notebook',
                'description': 'From import',
                'created_at': '2026-01-15 10:00:00',
                'entries': [
                    {
                        'type': 'text',
                        'content': 'Entry content',
                        'title': 'Entry 1',
                        'created_at': '2026-01-15 10:01:00'
                    }
                ]
            }
        ]
        
        stats = self.exporter.import_notebooks(notebooks)
        
        self.assertEqual(stats.imported, 1)
        self.assertEqual(stats.skipped, 0)
        
        all_notebooks = self.notebook_db.get_notebooks()
        self.assertEqual(len(all_notebooks), 1)
        self.assertEqual(all_notebooks[0]['name'], 'Imported Notebook')
        
        # Verify entries were imported
        entries = self.notebook_db.get_entries(all_notebooks[0]['id'])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['content'], 'Entry content')

    def test_full_export_import_cycle(self):
        """Test complete export/import cycle with duplicate detection."""
        # Create sample data
        self.db.save("test1.wav", "Recording 1 text", 10.0, "Recording 1")
        self.db.save("test2.wav", "Recording 2 text", 20.0, "Recording 2")
        self.db.save_chat_session("Chat 1", "All", "[]")
        nb_id = self.notebook_db.create_notebook("Notebook 1")
        self.notebook_db.add_text_entry(nb_id, "Note content", "Note 1")
        
        # Export
        self.exporter.export_all(self.export_file)
        
        # Import to the SAME database (should detect all as duplicates)
        result = self.exporter.import_all(self.export_file)
        
        self.assertTrue(result.success)
        self.assertEqual(result.records.imported, 0)
        self.assertEqual(result.records.skipped, 2)
        self.assertEqual(result.chat_sessions.imported, 0)
        self.assertEqual(result.chat_sessions.skipped, 1)
        self.assertEqual(result.notebooks.imported, 0)
        self.assertEqual(result.notebooks.skipped, 1)

    def test_import_to_fresh_database(self):
        """Test import to a fresh database (no duplicates)."""
        # Create sample data
        self.db.save("test.wav", "Hello World", 10.0, "Test Recording")
        self.db.save_chat_session("Chat 1", "All", "[]")
        nb_id = self.notebook_db.create_notebook("Test Notebook")
        self.notebook_db.add_text_entry(nb_id, "Note", "Title")
        
        # Export
        self.exporter.export_all(self.export_file)
        
        # Create fresh databases
        fresh_db_name = "fresh_db.sqlite"
        fresh_notebook_db_name = "fresh_notebooks.db"
        
        try:
            fresh_db = DBManager(fresh_db_name)
            fresh_notebook_db = NotebookDBManager(fresh_notebook_db_name)
            fresh_exporter = DataExporter(fresh_db, fresh_notebook_db)
            
            # Import
            result = fresh_exporter.import_all(self.export_file)
            
            self.assertTrue(result.success)
            self.assertEqual(result.records.imported, 1)
            self.assertEqual(result.records.skipped, 0)
            self.assertEqual(result.chat_sessions.imported, 1)
            self.assertEqual(result.chat_sessions.skipped, 0)
            self.assertEqual(result.notebooks.imported, 1)
            self.assertEqual(result.notebooks.skipped, 0)
            
            # Verify data
            self.assertEqual(len(fresh_db.fetch_all()), 1)
            self.assertEqual(len(fresh_db.fetch_chat_sessions()), 1)
            self.assertEqual(len(fresh_notebook_db.get_notebooks()), 1)
            
        finally:
            for f in [fresh_db_name, fresh_notebook_db_name]:
                if os.path.exists(f):
                    os.remove(f)

    def test_import_invalid_file(self):
        """Test import with invalid/missing file."""
        result = self.exporter.import_all("nonexistent_file.json")
        
        self.assertFalse(result.success)
        self.assertIn("Failed to read import file", result.error_message)


class TestImportStats(unittest.TestCase):
    """Test cases for ImportStats dataclass."""

    def test_default_values(self):
        """Test ImportStats has correct default values."""
        stats = ImportStats()
        
        self.assertEqual(stats.imported, 0)
        self.assertEqual(stats.skipped, 0)
        self.assertEqual(stats.errors, 0)
        self.assertEqual(stats.error_messages, [])


class TestImportResult(unittest.TestCase):
    """Test cases for ImportResult dataclass."""

    def test_default_values(self):
        """Test ImportResult has correct default values."""
        result = ImportResult()
        
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertIsInstance(result.records, ImportStats)
        self.assertIsInstance(result.chat_sessions, ImportStats)
        self.assertIsInstance(result.notebooks, ImportStats)


if __name__ == '__main__':
    unittest.main()
