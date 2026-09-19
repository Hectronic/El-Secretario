import gc
import os
import sqlite3
import time
from datetime import date

from src.database import DBManager

from ._database_case import DatabaseRepositoryTestCase


class TestTasksRepository(DatabaseRepositoryTestCase):
    def test_save_task_from_record_infers_origin_and_tags(self):
        rec_id = self.db.save('meeting.wav', 'Tx', 10.0, 'Weekly Sync')
        self.db.update_tags(rec_id, 'team, roadmap')
        task_id = self.db.save_task(rec_id, 'Prepare follow-up email')
        tasks = self.db.get_tasks_by_record(rec_id)
        task = next((t for t in tasks if t['id'] == task_id))
        self.assertEqual(task['task_origin'], 'Weekly Sync')
        self.assertEqual(task['tags'], 'team, roadmap')
        self.assertEqual(task['is_ai_generated'], 0)

    def test_ai_task_flag_and_helpers(self):
        rec_id = self.db.save('meeting.wav', 'Tx', 10.0, 'Weekly Sync')
        self.db.save_task(rec_id, 'AI action', is_ai_generated=True)
        self.db.save_task(rec_id, 'Manual action')
        self.assertTrue(self.db.has_ai_tasks_for_record(rec_id))
        self.db.delete_ai_tasks_by_record(rec_id)
        tasks = self.db.get_tasks_by_record(rec_id)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['content'], 'Manual action')
        self.assertEqual(tasks[0]['is_ai_generated'], 0)

    def test_save_generic_task_has_no_origin(self):
        today = date.today().isoformat()
        task_id = self.db.save_task(record_id=None, content='Buy office supplies', day_date=today, week_start=self.db._week_sunday(today))
        tasks = self.db.get_tasks_by_date(today)
        task = next((t for t in tasks if t['id'] == task_id))
        self.assertTrue(task.get('task_origin') in (None, ''))

    def test_task_origin_updates_when_record_title_changes(self):
        rec_id = self.db.save('meeting.wav', 'Tx', 10.0, 'Old Title')
        task_id = self.db.save_task(rec_id, 'Action item')
        self.db.update_title(rec_id, 'New Title')
        tasks = self.db.get_tasks_by_record(rec_id)
        task = next((t for t in tasks if t['id'] == task_id))
        self.assertEqual(task['task_origin'], 'New Title')
        self.assertEqual(task['record_title'], 'New Title')

    def test_record_tag_updates_propagate_to_associated_tasks(self):
        rec_id = self.db.save('meeting.wav', 'Tx', 10.0, 'Tag Source')
        self.db.update_tags(rec_id, 'alpha, beta')
        task_id = self.db.save_task(rec_id, 'Follow up')
        self.db.update_tags(rec_id, 'gamma, delta')
        task = next((t for t in self.db.get_tasks_by_record(rec_id) if t['id'] == task_id))
        self.assertEqual(task['tags'], 'gamma, delta')
        self.assertEqual(task['record_tags'], 'gamma, delta')

    def test_update_task_details_updates_content_notes_and_tags(self):
        today = date.today().isoformat()
        task_id = self.db.save_task(record_id=None, content='Initial task', day_date=today, week_start=self.db._week_sunday(today))
        self.db.update_task_details(task_id, 'Updated content', 'Some notes', 'alpha, beta')
        task = next((t for t in self.db.get_tasks_by_date(today) if t['id'] == task_id))
        self.assertEqual(task['content'], 'Updated content')
        self.assertEqual(task['notes'], 'Some notes')
        self.assertEqual(task['tags'], 'alpha, beta')

    def test_get_tasks_by_date_with_multi_tag_filter_matches_any_tag(self):
        today = date.today().isoformat()
        rec1 = self.db.save('a.wav', 'Tx A', 10.0, 'A')
        rec2 = self.db.save('b.wav', 'Tx B', 10.0, 'B')
        self.db.update_tags(rec1, 'work, home')
        self.db.update_tags(rec2, 'personal')
        self.db.save_task(rec1, 'Task A1', 'work, home')
        self.db.save_task(rec2, 'Task B1', 'personal')
        tasks = self.db.get_tasks_by_date(today, 'work,home')
        contents = [t['content'] for t in tasks]
        self.assertIn('Task A1', contents)
        self.assertNotIn('Task B1', contents)
        tasks_with_spaces = self.db.get_tasks_by_date(today, 'work, home')
        contents_with_spaces = [t['content'] for t in tasks_with_spaces]
        self.assertIn('Task A1', contents_with_spaces)

    def test_toggle_completion_sets_and_clears_completed_at(self):
        today = date.today().isoformat()
        task_id = self.db.save_task(record_id=None, content='Mark me done', day_date=today, week_start=self.db._week_sunday(today))
        self.db.toggle_task_completion(task_id, True)
        tasks = self.db.get_tasks_by_date(today)
        task = next((t for t in tasks if t['id'] == task_id))
        self.assertEqual(task['is_completed'], 1)
        self.assertIsNotNone(task['completed_at'])
        self.db.toggle_task_completion(task_id, False)
        tasks = self.db.get_tasks_by_date(today)
        task = next((t for t in tasks if t['id'] == task_id))
        self.assertEqual(task['is_completed'], 0)
        self.assertIsNone(task['completed_at'])

    def test_weekly_task_snapshot_groups(self):
        week_sunday = '2026-02-15'
        created_id = self.db.save_task(None, 'Created this week', day_date='2026-02-10', week_start=week_sunday)
        completed_id = self.db.save_task(None, 'Completed this week', day_date='2026-02-08', week_start='2026-02-08')
        pending_old_id = self.db.save_task(None, 'Pending from before', day_date='2026-02-01', week_start='2026-02-01')
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE tasks SET created_at = ? WHERE id = ?', ('2026-02-10 10:00:00', created_id))
            c.execute('UPDATE tasks SET created_at = ?, is_completed = 1, completed_at = ? WHERE id = ?', ('2026-02-03 10:00:00', '2026-02-12 12:00:00', completed_id))
            c.execute('UPDATE tasks SET created_at = ?, is_completed = 0, completed_at = NULL WHERE id = ?', ('2026-02-02 08:00:00', pending_old_id))
            conn.commit()
        snapshot = self.db.get_weekly_task_snapshot(week_sunday)
        created_ids = {t['id'] for t in snapshot['created_this_week']}
        completed_ids = {t['id'] for t in snapshot['completed_this_week']}
        pending_ids = {t['id'] for t in snapshot['pending_from_before']}
        self.assertIn(created_id, created_ids)
        self.assertIn(completed_id, completed_ids)
        self.assertIn(pending_old_id, pending_ids)

    def test_get_tasks_by_date_range_with_tag_filter(self):
        in_range = self.db.save('in.wav', 'Tx', 10.0, 'In Range')
        out_range = self.db.save('out.wav', 'Tx', 10.0, 'Out Range')
        self.db.update_tags(in_range, 'alpha, team')
        self.db.update_tags(out_range, 'beta')
        t1 = self.db.save_task(in_range, 'Task in')
        t2 = self.db.save_task(out_range, 'Task out')
        with self.db.get_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE tasks SET day_date = ?, week_start = ?, created_at = ? WHERE id = ?', ('2026-02-11', '2026-02-15', '2026-02-11 09:00:00', t1))
            c.execute('UPDATE tasks SET day_date = ?, week_start = ?, created_at = ? WHERE id = ?', ('2026-02-20', '2026-02-22', '2026-02-20 09:00:00', t2))
            conn.commit()
        tasks = self.db.get_tasks_by_date_range('2026-02-10', '2026-02-15', tags_filter='alpha')
        ids = {t['id'] for t in tasks}
        self.assertIn(t1, ids)
        self.assertNotIn(t2, ids)
