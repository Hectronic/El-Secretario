
import unittest
import os
import sqlite3
import sys
# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import DBManager
from datetime import datetime, timedelta

class TestWeeklySummarySunday(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_weekly_sunday.sqlite"
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
        # We need to initialize the DB with the OLD schema/data format to test migration
        # But DBManager.init_db() now has the migration.
        # So we'll manually create the table and insert old data, then run DBManager.
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                summary TEXT NOT NULL,
                tags_filter TEXT,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(week_start, tags_filter)
            )
        ''')
        # Insert a Monday date (2026-02-09 is Monday)
        cursor.execute('''
            INSERT INTO weekly_summaries (week_start, summary, tags_filter, generated_at)
            VALUES ('2026-02-09', 'Old Summary', '', '2026-02-09 10:00:00')
        ''')
        conn.commit()
        conn.close()
        
        # Now init with DBManager to trigger migration
        self.db = DBManager(self.db_name)

    def tearDown(self):
        if hasattr(self, 'db'):
            del self.db
        if os.path.exists(self.db_name):
            try:
                os.remove(self.db_name)
            except:
                pass

    def test_migration(self):
        # The Monday 2026-02-09 should have been migrated to Sunday 2026-02-15
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT week_start, generated_at FROM weekly_summaries WHERE summary = 'Old Summary'")
            row = cursor.fetchone()
            self.assertEqual(row['week_start'], "2026-02-15")
            self.assertTrue(row['generated_at'].endswith("23:59:59"))

    def test_get_weeks_with_content(self):
        # Create a record on a Thursday (2026-02-12)
        # SQLite weekday 0 (Sunday) for 2026-02-12 should be 2026-02-15
        self.db.save("audio.wav", "Transcription", 10.0, "Title")
        # Manually update created_at to 2026-02-12
        with self.db.get_connection() as conn:
            conn.execute("UPDATE records SET created_at = '2026-02-12 10:00:00'")
            conn.commit()
            
        weeks = self.db.get_weeks_with_content()
        self.assertIn("2026-02-15", weeks)

    def test_get_weeks_without_summary(self):
        # Record on 2026-02-12 -> Sunday 2026-02-15
        self.db.save("audio.wav", "Transcription", 10.0, "Title")
        # Also need a weekly summary record to check exclusion
        # We already have 'Old Summary' migrated to 2026-02-15
        
        with self.db.get_connection() as conn:
            conn.execute("UPDATE records SET created_at = '2026-02-12 10:00:00'")
            conn.commit()
            
        # 2026-02-15 already has a summary from migration (Old Summary)
        # So it should NOT be in weeks_without_summary
        weeks = self.db.get_weeks_without_summary()
        self.assertNotIn("2026-02-15", weeks)
        
        # Add record for another week (2026-02-05 which is Thursday -> Sunday 2026-02-08)
        self.db.save("audio2.wav", "Transcription 2", 10.0, "Title 2")
        with self.db.get_connection() as conn:
            conn.execute("UPDATE records SET created_at = '2026-02-05 10:00:00' WHERE title = 'Title 2'")
            conn.commit()
            
        weeks = self.db.get_weeks_without_summary()
        self.assertIn("2026-02-08", weeks)

if __name__ == '__main__':
    unittest.main()
