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

    def test_recording_notes_are_persisted_and_composed_for_ai(self):
        record_id = self.db.save("test.wav", "Meeting transcription", 10.0, "Title")
        self.db.update_recording_notes(record_id, "Remember to send proposal.")

        record = self.db.fetch_record(record_id)
        self.assertEqual(record["recording_notes"], "Remember to send proposal.")

        ai_text = self.db.get_record_ai_text(record_id)
        self.assertIn("Meeting transcription", ai_text)
        self.assertIn("Remember to send proposal.", ai_text)

    def test_records_with_only_notes_are_detected_as_content(self):
        record_id = self.db.save("test.wav", "", 10.0, "Title", recording_notes="Only notes")
        dates = self.db.get_dates_with_content()
        self.assertTrue(len(dates) >= 1)

        pending_no_summary = self.db.get_records_without_summary()
        ids = [r["id"] for r in pending_no_summary]
        self.assertIn(record_id, ids)

    def test_save_task_from_record_infers_origin_and_tags(self):
        rec_id = self.db.save("meeting.wav", "Tx", 10.0, "Weekly Sync")
        self.db.update_tags(rec_id, "team, roadmap")

        task_id = self.db.save_task(rec_id, "Prepare follow-up email")
        tasks = self.db.get_tasks_by_record(rec_id)
        task = next(t for t in tasks if t["id"] == task_id)

        self.assertEqual(task["task_origin"], "Weekly Sync")
        self.assertEqual(task["tags"], "team, roadmap")

    def test_save_generic_task_has_no_origin(self):
        today = date.today().isoformat()
        task_id = self.db.save_task(
            record_id=None,
            content="Buy office supplies",
            day_date=today,
            week_start=self.db._week_sunday(today),
        )
        tasks = self.db.get_tasks_by_date(today)
        task = next(t for t in tasks if t["id"] == task_id)
        self.assertTrue(task.get("task_origin") in (None, ""))

    def test_task_origin_updates_when_record_title_changes(self):
        rec_id = self.db.save("meeting.wav", "Tx", 10.0, "Old Title")
        task_id = self.db.save_task(rec_id, "Action item")

        self.db.update_title(rec_id, "New Title")
        tasks = self.db.get_tasks_by_record(rec_id)
        task = next(t for t in tasks if t["id"] == task_id)

        self.assertEqual(task["task_origin"], "New Title")
        self.assertEqual(task["record_title"], "New Title")

    def test_record_tag_updates_propagate_to_associated_tasks(self):
        rec_id = self.db.save("meeting.wav", "Tx", 10.0, "Tag Source")
        self.db.update_tags(rec_id, "alpha, beta")
        task_id = self.db.save_task(rec_id, "Follow up")

        self.db.update_tags(rec_id, "gamma, delta")
        task = next(t for t in self.db.get_tasks_by_record(rec_id) if t["id"] == task_id)

        self.assertEqual(task["tags"], "gamma, delta")
        self.assertEqual(task["record_tags"], "gamma, delta")

    def test_update_task_details_updates_content_notes_and_tags(self):
        today = date.today().isoformat()
        task_id = self.db.save_task(
            record_id=None,
            content="Initial task",
            day_date=today,
            week_start=self.db._week_sunday(today),
        )

        self.db.update_task_details(task_id, "Updated content", "Some notes", "alpha, beta")
        task = next(t for t in self.db.get_tasks_by_date(today) if t["id"] == task_id)

        self.assertEqual(task["content"], "Updated content")
        self.assertEqual(task["notes"], "Some notes")
        self.assertEqual(task["tags"], "alpha, beta")

    def test_get_latest_recording_day_without_daily_summary(self):
        rec_day_1 = self.db.save("d1.wav", "Tx1", 10.0, "D1")
        rec_day_2 = self.db.save("d2.wav", "Tx2", 10.0, "D2")
        rec_day_3 = self.db.save("d3.wav", "Tx3", 10.0, "D3")

        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE records SET created_at = ? WHERE id = ?", ("2026-02-10 10:00:00", rec_day_1))
            c.execute("UPDATE records SET created_at = ? WHERE id = ?", ("2026-02-11 10:00:00", rec_day_2))
            c.execute("UPDATE records SET created_at = ? WHERE id = ?", ("2026-02-12 10:00:00", rec_day_3))
            conn.commit()

        self.db.save_daily_summary("2026-02-12", "done")
        target = self.db.get_latest_recording_day_without_daily_summary("2026-02-13")
        self.assertEqual(target, "2026-02-11")

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
                self.assertIn("completed_at", cols)
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

    def test_toggle_completion_sets_and_clears_completed_at(self):
        today = date.today().isoformat()
        task_id = self.db.save_task(
            record_id=None,
            content="Mark me done",
            day_date=today,
            week_start=self.db._week_sunday(today),
        )
        self.db.toggle_task_completion(task_id, True)
        tasks = self.db.get_tasks_by_date(today)
        task = next(t for t in tasks if t["id"] == task_id)
        self.assertEqual(task["is_completed"], 1)
        self.assertIsNotNone(task["completed_at"])

        self.db.toggle_task_completion(task_id, False)
        tasks = self.db.get_tasks_by_date(today)
        task = next(t for t in tasks if t["id"] == task_id)
        self.assertEqual(task["is_completed"], 0)
        self.assertIsNone(task["completed_at"])

    def test_weekly_task_snapshot_groups(self):
        week_sunday = "2026-02-15"

        created_id = self.db.save_task(None, "Created this week", day_date="2026-02-10", week_start=week_sunday)
        completed_id = self.db.save_task(None, "Completed this week", day_date="2026-02-08", week_start="2026-02-08")
        pending_old_id = self.db.save_task(None, "Pending from before", day_date="2026-02-01", week_start="2026-02-01")

        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE tasks SET created_at = ? WHERE id = ?", ("2026-02-10 10:00:00", created_id))
            c.execute("UPDATE tasks SET created_at = ?, is_completed = 1, completed_at = ? WHERE id = ?", ("2026-02-03 10:00:00", "2026-02-12 12:00:00", completed_id))
            c.execute("UPDATE tasks SET created_at = ?, is_completed = 0, completed_at = NULL WHERE id = ?", ("2026-02-02 08:00:00", pending_old_id))
            conn.commit()

        snapshot = self.db.get_weekly_task_snapshot(week_sunday)
        created_ids = {t["id"] for t in snapshot["created_this_week"]}
        completed_ids = {t["id"] for t in snapshot["completed_this_week"]}
        pending_ids = {t["id"] for t in snapshot["pending_from_before"]}

        self.assertIn(created_id, created_ids)
        self.assertIn(completed_id, completed_ids)
        self.assertIn(pending_old_id, pending_ids)

    def test_get_tasks_by_date_range_with_tag_filter(self):
        in_range = self.db.save("in.wav", "Tx", 10.0, "In Range")
        out_range = self.db.save("out.wav", "Tx", 10.0, "Out Range")
        self.db.update_tags(in_range, "alpha, team")
        self.db.update_tags(out_range, "beta")

        t1 = self.db.save_task(in_range, "Task in")
        t2 = self.db.save_task(out_range, "Task out")

        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE tasks SET day_date = ?, week_start = ?, created_at = ? WHERE id = ?", ("2026-02-11", "2026-02-15", "2026-02-11 09:00:00", t1))
            c.execute("UPDATE tasks SET day_date = ?, week_start = ?, created_at = ? WHERE id = ?", ("2026-02-20", "2026-02-22", "2026-02-20 09:00:00", t2))
            conn.commit()

        tasks = self.db.get_tasks_by_date_range("2026-02-10", "2026-02-15", tags_filter="alpha")
        ids = {t["id"] for t in tasks}
        self.assertIn(t1, ids)
        self.assertNotIn(t2, ids)

if __name__ == '__main__':
    unittest.main()
