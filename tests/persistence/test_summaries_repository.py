import gc
import os
import sqlite3
import time
from datetime import date

from src.database import DBManager

from ._database_case import DatabaseRepositoryTestCase


class TestSummariesRepository(DatabaseRepositoryTestCase):
    def test_get_latest_recording_day_without_daily_summary(self):
        rec_day_1 = self.db.save('d1.wav', 'Tx1', 10.0, 'D1')
        rec_day_2 = self.db.save('d2.wav', 'Tx2', 10.0, 'D2')
        rec_day_3 = self.db.save('d3.wav', 'Tx3', 10.0, 'D3')
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE records SET created_at = ? WHERE id = ?', ('2026-02-10 10:00:00', rec_day_1))
            c.execute('UPDATE records SET created_at = ? WHERE id = ?', ('2026-02-11 10:00:00', rec_day_2))
            c.execute('UPDATE records SET created_at = ? WHERE id = ?', ('2026-02-12 10:00:00', rec_day_3))
            conn.commit()
        self.db.save_daily_summary('2026-02-12', 'done')
        target = self.db.get_latest_recording_day_without_daily_summary('2026-02-13')
        self.assertEqual(target, '2026-02-11')

    def test_daily_summaries_by_range(self):
        self.db.save_daily_summary('2026-02-09', 'Summary 1')
        self.db.save_daily_summary('2026-02-10', 'Summary 2')
        self.db.save_daily_summary('2026-02-11', 'Summary 3')
        summaries = self.db.fetch_daily_summaries_by_range('2026-02-09', '2026-02-10')
        self.assertEqual(len(summaries), 2)
        self.assertEqual(summaries[0]['date'], '2026-02-10')
        self.assertEqual(summaries[1]['date'], '2026-02-09')
