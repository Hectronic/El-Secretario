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
from datetime import datetime, timedelta
from src.database import DBManager

class TestCalendarMultiSelection(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_calendar_multi.db"
        self.db = DBManager(self.db_path)
        
        # Create dummy records
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        
        # Clear existing
        with self.db.get_connection() as conn:
            conn.cursor().execute("DELETE FROM records")
            conn.commit()
            
        # Add records
        # Today: 2 records
        self.db.save("rec1.wav", "Text 1", 10.0, title="Today 1")
        self.db.save("rec2.wav", "Text 2", 20.0, title="Today 2")
        
        # Yesterday: 1 record
        # We need to manually update created_at because save() uses now()
        rec_id = self.db.save("rec3.wav", "Text 3", 30.0, title="Yesterday 1")
        with self.db.get_connection() as conn:
            conn.cursor().execute(f"UPDATE records SET created_at = '{self.yesterday} 12:00:00' WHERE id = {rec_id}")
            conn.commit()
            
        # Two days ago: 1 record
        rec_id = self.db.save("rec4.wav", "Text 4", 40.0, title="Two Days Ago 1")
        with self.db.get_connection() as conn:
            conn.cursor().execute(f"UPDATE records SET created_at = '{self.two_days_ago} 12:00:00' WHERE id = {rec_id}")
            conn.commit()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_fetch_by_single_date(self):
        records = self.db.fetch_by_dates([self.today])
        self.assertEqual(len(records), 2)
        self.assertTrue(all(r['title'].startswith("Today") for r in records))

    def test_fetch_by_multiple_dates(self):
        records = self.db.fetch_by_dates([self.today, self.two_days_ago])
        self.assertEqual(len(records), 3) # 2 from today, 1 from two days ago
        titles = [r['title'] for r in records]
        self.assertIn("Today 1", titles)
        self.assertIn("Today 2", titles)
        self.assertIn("Two Days Ago 1", titles)
        self.assertNotIn("Yesterday 1", titles)

    def test_fetch_by_dates_empty(self):
        records = self.db.fetch_by_dates([])
        self.assertEqual(len(records), 0)

    def test_fetch_by_dates_no_match(self):
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        records = self.db.fetch_by_dates([future_date])
        self.assertEqual(len(records), 0)

if __name__ == '__main__':
    unittest.main()
