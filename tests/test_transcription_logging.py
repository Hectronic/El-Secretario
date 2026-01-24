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

import os
import sys
import unittest
import shutil
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import DBManager

class TestTranscriptionLogging(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_transcription.db"
        self.db = DBManager(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_log_transcription(self):
        # Create a dummy record first
        self.db.save("test.wav", "Test transcription", 10.0)
        records = self.db.fetch_all()
        self.assertTrue(len(records) > 0)
        record_id = records[0]['id']

        # Log transcription
        self.db.log_transcription(
            model_name="base",
            audio_duration=10.0,
            audio_size_bytes=1024,
            transcription_time_seconds=2.5,
            record_id=record_id
        )

        # Verify log entry
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transcription_logs WHERE record_id = ?", (record_id,))
            log = cursor.fetchone()
            
            self.assertIsNotNone(log)
            self.assertEqual(log['model_name'], "base")
            self.assertEqual(log['audio_duration'], 10.0)
            self.assertEqual(log['audio_size_bytes'], 1024)
            self.assertEqual(log['transcription_time_seconds'], 2.5)
            self.assertEqual(log['record_id'], record_id)

if __name__ == '__main__':
    unittest.main()
