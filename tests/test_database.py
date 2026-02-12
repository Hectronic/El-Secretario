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

if __name__ == '__main__':
    unittest.main()
