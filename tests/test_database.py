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
import sqlite3
from datetime import date
from src.database import DBManager

class TestDBManager(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_db.sqlite"
        self.db = DBManager(self.db_name)

    def tearDown(self):
        if os.path.exists(self.db_name):
            os.remove(self.db_name)

    def test_init_db(self):
        self.assertTrue(os.path.exists(self.db_name))
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records'")
            self.assertIsNotNone(cursor.fetchone())

    def test_save_and_fetch(self):
        self.db.save("test.wav", "Transcription", 10.0, "Title")
        records = self.db.fetch_all()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['title'], "Title")
        self.assertEqual(records[0]['transcription'], "Transcription")

    def test_update_methods(self):
        self.db.save("test.wav", "Transcription", 10.0)
        records = self.db.fetch_all()
        record_id = records[0]['id']

        self.db.update_title(record_id, "New Title")
        self.db.update_transcription(record_id, "New Text")
        self.db.update_tags(record_id, "tag1, tag2")
        self.db.update_ai_content(record_id, summary="Summary", cleaned_text="Cleaned")

        updated_record = self.db.fetch_all()[0]
        self.assertEqual(updated_record['title'], "New Title")
        self.assertEqual(updated_record['transcription'], "New Text")
        self.assertEqual(updated_record['tags'], "tag1, tag2")
        self.assertEqual(updated_record['summary'], "Summary")
        self.assertEqual(updated_record['cleaned_text'], "Cleaned")

    def test_chat_sessions(self):
        session_id = self.db.save_chat_session("Chat 1", "All", "[]")
        sessions = self.db.fetch_chat_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]['name'], "Chat 1")

        self.db.update_chat_session(session_id, "[{'role': 'user'}]")
        sessions = self.db.fetch_chat_sessions()
        self.assertEqual(sessions[0]['messages'], "[{'role': 'user'}]")

        self.db.delete_chat_session(session_id)
        sessions = self.db.fetch_chat_sessions()
        self.assertEqual(len(sessions), 0)

    def test_daily_summaries_by_range(self):
        self.db.save_daily_summary("2026-02-09", "Summary 1")
        self.db.save_daily_summary("2026-02-10", "Summary 2")
        self.db.save_daily_summary("2026-02-11", "Summary 3")
        
        # Range: 9 to 10
        summaries = self.db.fetch_daily_summaries_by_range("2026-02-09", "2026-02-10")
        self.assertEqual(len(summaries), 2)
        # Should be descending order by date
        self.assertEqual(summaries[0]['date'], "2026-02-10")
        self.assertEqual(summaries[1]['date'], "2026-02-09")

    def test_get_tasks_by_date_with_multi_tag_filter_matches_any_tag(self):
        today = date.today().isoformat()
        # Same day, different record tags
        rec1 = self.db.save("a.wav", "Tx A", 10.0, "A")
        rec2 = self.db.save("b.wav", "Tx B", 10.0, "B")
        self.db.update_tags(rec1, "work, home")
        self.db.update_tags(rec2, "personal")

        self.db.save_task(rec1, "Task A1", "work, home")
        self.db.save_task(rec2, "Task B1", "personal")

        # Multi-tag filter should behave as OR (match ANY tag), not exact full string.
        tasks = self.db.get_tasks_by_date(today, "work,home")
        contents = [t["content"] for t in tasks]

        self.assertIn("Task A1", contents)
        self.assertNotIn("Task B1", contents)

        # Spaces in filter should not change behavior.
        tasks_with_spaces = self.db.get_tasks_by_date(today, "work, home")
        contents_with_spaces = [t["content"] for t in tasks_with_spaces]
        self.assertIn("Task A1", contents_with_spaces)

    def test_legacy_tasks_schema_is_migrated_on_startup(self):
        legacy_db = "test_legacy_db.sqlite"
        try:
            with sqlite3.connect(legacy_db) as conn:
                c = conn.cursor()
                c.execute('''
                    CREATE TABLE records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        filename TEXT,
                        duration REAL,
                        transcription TEXT,
                        title TEXT,
                        tags TEXT,
                        summary TEXT,
                        cleaned_text TEXT,
                        is_favorite INTEGER DEFAULT 0,
                        is_diarized INTEGER DEFAULT 0,
                        transcription_model TEXT,
                        processing_attempts INTEGER DEFAULT 0,
                        last_error TEXT
                    )
                ''')
                c.execute('''
                    CREATE TABLE tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        record_id INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        tags TEXT,
                        is_completed INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                c.execute(
                    "INSERT INTO records (created_at, filename, duration, transcription, title) VALUES (?, ?, ?, ?, ?)",
                    ("2026-02-10 10:00:00", "x.wav", 1.0, "tx", "Rec A"),
                )
                c.execute(
                    "INSERT INTO tasks (record_id, content, tags, is_completed, created_at) VALUES (?, ?, ?, ?, ?)",
                    (1, "Legacy task", "x", 0, "2026-02-10 11:00:00"),
                )
                conn.commit()

            migrated = DBManager(legacy_db)
            _ = migrated.fetch_all()

            with sqlite3.connect(legacy_db) as conn:
                c = conn.cursor()
                c.execute("PRAGMA table_info(tasks)")
                cols = {row[1]: row for row in c.fetchall()}
                self.assertIn("day_date", cols)
                self.assertIn("week_start", cols)
                self.assertIn("notes", cols)
                self.assertIn("custom_order", cols)
                self.assertEqual(cols["record_id"][3], 0)  # not null flag must be off

                c.execute("SELECT record_id, day_date, week_start, content FROM tasks LIMIT 1")
                row = c.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], 1)
                self.assertEqual(row[1], "2026-02-10")
                self.assertEqual(row[2], "2026-02-15")
                self.assertEqual(row[3], "Legacy task")
        finally:
            if os.path.exists(legacy_db):
                os.remove(legacy_db)

if __name__ == '__main__':
    unittest.main()
