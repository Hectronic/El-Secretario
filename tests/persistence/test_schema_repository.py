import gc
import os
import sqlite3
import time
from datetime import date

from src.database import DBManager

from ._database_case import DatabaseRepositoryTestCase


class TestSchemaRepository(DatabaseRepositoryTestCase):
    def test_init_db(self):
        self.assertTrue(os.path.exists(self.db_name))
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records'")
            self.assertIsNotNone(cursor.fetchone())

    def test_legacy_tasks_schema_is_migrated_on_startup(self):
        legacy_db = 'test_legacy_db.sqlite'
        migrated = None
        try:
            if os.path.exists(legacy_db):
                os.remove(legacy_db)
            with sqlite3.connect(legacy_db) as conn:
                c = conn.cursor()
                c.execute('\n                    CREATE TABLE records (\n                        id INTEGER PRIMARY KEY AUTOINCREMENT,\n                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,\n                        filename TEXT,\n                        duration REAL,\n                        transcription TEXT,\n                        title TEXT,\n                        tags TEXT,\n                        summary TEXT,\n                        cleaned_text TEXT,\n                        is_favorite INTEGER DEFAULT 0,\n                        is_diarized INTEGER DEFAULT 0,\n                        transcription_model TEXT,\n                        processing_attempts INTEGER DEFAULT 0,\n                        last_error TEXT\n                    )\n                ')
                c.execute('\n                    CREATE TABLE tasks (\n                        id INTEGER PRIMARY KEY AUTOINCREMENT,\n                        record_id INTEGER NOT NULL,\n                        content TEXT NOT NULL,\n                        tags TEXT,\n                        is_completed INTEGER DEFAULT 0,\n                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP\n                    )\n                ')
                c.execute('INSERT INTO records (created_at, filename, duration, transcription, title) VALUES (?, ?, ?, ?, ?)', ('2026-02-10 10:00:00', 'x.wav', 1.0, 'tx', 'Rec A'))
                c.execute('INSERT INTO tasks (record_id, content, tags, is_completed, created_at) VALUES (?, ?, ?, ?, ?)', (1, 'Legacy task', 'x', 0, '2026-02-10 11:00:00'))
                conn.commit()
            migrated = DBManager(legacy_db)
            _ = migrated.fetch_all()
            with sqlite3.connect(legacy_db) as conn:
                c = conn.cursor()
                c.execute('PRAGMA table_info(tasks)')
                cols = {row[1]: row for row in c.fetchall()}
                self.assertIn('day_date', cols)
                self.assertIn('week_start', cols)
                self.assertIn('notes', cols)
                self.assertIn('custom_order', cols)
                self.assertIn('completed_at', cols)
                self.assertEqual(cols['record_id'][3], 0)
                c.execute('SELECT record_id, day_date, week_start, content FROM tasks LIMIT 1')
                row = c.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], 1)
                self.assertEqual(row[1], '2026-02-10')
                self.assertEqual(row[2], '2026-02-15')
                self.assertEqual(row[3], 'Legacy task')
        finally:
            migrated = None
            gc.collect()
            if os.path.exists(legacy_db):
                for _ in range(5):
                    try:
                        os.remove(legacy_db)
                        break
                    except PermissionError:
                        time.sleep(0.2)
