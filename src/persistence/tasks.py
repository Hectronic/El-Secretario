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


from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional



class TasksRepository:
    def _week_sunday(self, date_str: str) -> str:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        days_until_sunday = 6 - dt.weekday()
        return (dt + timedelta(days=days_until_sunday)).date().isoformat()

    def save_task(self, record_id: Optional[int], content: str, tags: Optional[str] = None,
                  day_date: Optional[str] = None, week_start: Optional[str] = None,
                  notes: Optional[str] = None, task_origin: Optional[str] = None,
                  is_ai_generated: bool = False) -> int:
        """
        Save a task with optional scope:
        - week only: week_start
        - day + week: day_date + week_start
        - record + day + week: record_id (+ inferred day/week if omitted)
        """
        if not content or not content.strip():
            raise ValueError("Task content cannot be empty.")

        resolved_record_id = record_id
        resolved_day_date = day_date
        resolved_week_start = week_start
        resolved_tags = tags.strip() if isinstance(tags, str) and tags.strip() else None
        resolved_origin = task_origin.strip() if isinstance(task_origin, str) and task_origin.strip() else None

        if resolved_record_id is not None:
            rec = self.fetch_record(resolved_record_id)
            if not isinstance(rec, dict):
                raise ValueError(f"Recording {resolved_record_id} does not exist.")
            rec_day = str(rec.get("created_at", ""))[:10]
            rec_week = self._week_sunday(rec_day)
            rec_tags = (rec.get("tags") or "").strip()
            rec_title = (rec.get("title") or "").strip()
            if not resolved_day_date:
                resolved_day_date = rec_day
            if not resolved_week_start:
                resolved_week_start = rec_week
            if resolved_day_date != rec_day:
                raise ValueError("Task day_date must match recording date.")
            if resolved_week_start != rec_week:
                raise ValueError("Task week_start must match recording week.")
            if not resolved_tags and rec_tags:
                resolved_tags = rec_tags
            if not resolved_origin and rec_title:
                resolved_origin = rec_title
        else:
            if resolved_day_date and not resolved_week_start:
                resolved_week_start = self._week_sunday(resolved_day_date)
            if not resolved_week_start:
                raise ValueError("Task requires at least week_start.")

        if resolved_day_date and resolved_week_start:
            expected_week = self._week_sunday(resolved_day_date)
            if resolved_week_start != expected_week:
                raise ValueError("If task has day_date, week_start must be that day's week.")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tasks (record_id, day_date, week_start, content, task_origin, is_ai_generated, notes, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                resolved_record_id,
                resolved_day_date,
                resolved_week_start,
                content.strip(),
                resolved_origin,
                1 if is_ai_generated else 0,
                notes,
                resolved_tags,
            ))
            conn.commit()
            return cursor.lastrowid

    def delete_task(self, task_id: int) -> None:
        """Delete a single task by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.commit()

    def update_task_content(self, task_id: int, content: str) -> None:
        """Update the content of an existing task."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE tasks SET content = ? WHERE id = ?', (content, task_id))
            conn.commit()

    def update_task_notes(self, task_id: int, notes: Optional[str]) -> None:
        """Update notes of an existing task."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE tasks SET notes = ? WHERE id = ?', (notes, task_id))
            conn.commit()

    def update_task_content_and_notes(self, task_id: int, content: str, notes: Optional[str]) -> None:
        """Update content and notes of an existing task."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE tasks SET content = ?, notes = ? WHERE id = ?', (content, notes, task_id))
            conn.commit()

    def update_task_tags(self, task_id: int, tags: Optional[str]) -> None:
        """Update tags of an existing task."""
        clean_tags = tags.strip() if isinstance(tags, str) and tags.strip() else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE tasks SET tags = ? WHERE id = ?', (clean_tags, task_id))
            conn.commit()

    def update_task_details(self, task_id: int, content: str, notes: Optional[str], tags: Optional[str]) -> None:
        """Update content, notes and tags of an existing task."""
        clean_tags = tags.strip() if isinstance(tags, str) and tags.strip() else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE tasks SET content = ?, notes = ?, tags = ? WHERE id = ?',
                (content, notes, clean_tags, task_id),
            )
            conn.commit()

    def delete_tasks_by_record(self, record_id: int) -> None:
        """Delete all tasks associated with a record (e.g. before regenerating)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE record_id = ?', (record_id,))
            conn.commit()

    def delete_ai_tasks_by_record(self, record_id: int) -> None:
        """Delete only AI-generated tasks for a record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE record_id = ? AND is_ai_generated = 1', (record_id,))
            conn.commit()

    def has_ai_tasks_for_record(self, record_id: int) -> bool:
        """Return True if the record has AI-generated tasks."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM tasks WHERE record_id = ? AND is_ai_generated = 1 LIMIT 1',
                (record_id,),
            )
            return cursor.fetchone() is not None

    def get_tasks_by_record(self, record_id: int) -> List[Dict[str, Any]]:
        """Fetch all tasks for a specific recording."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT
                    t.*,
                    r.title as record_title,
                    r.tags as record_tags,
                    r.type as record_type
                FROM tasks t
                LEFT JOIN records r ON t.record_id = r.id
                WHERE t.record_id = ?
                ORDER BY t.created_at ASC
            ''', (record_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_tasks_by_date(self, date_str: str, tags_filter: Optional[str] = None, order_mode: str = "date") -> List[Dict[str, Any]]:
        """Fetch all tasks for a specific day, optionally filtered by tags."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT
                    t.*,
                    r.title as record_title,
                    r.tags as record_tags,
                    r.type as record_type
                FROM tasks t
                LEFT JOIN records r ON t.record_id = r.id
                WHERE t.day_date = ?
            '''
            params = [date_str]
            if tags_filter:
                # Keep filtering behavior consistent with recordings:
                # if multiple tags are provided, match records that contain ANY of them.
                tags = [t.strip() for t in str(tags_filter).split(",") if t and t.strip()]
                if tags:
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append("(COALESCE(r.tags, '') LIKE ? OR COALESCE(t.tags, '') LIKE ?)")
                        params.append(f"%{tag}%")
                        params.append(f"%{tag}%")
                    query += " AND (" + " OR ".join(tag_conditions) + ")"

            if order_mode == "custom":
                query += " ORDER BY COALESCE(t.custom_order, 999999999), t.created_at DESC, t.id DESC"
            else:
                query += " ORDER BY t.created_at ASC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_tasks_by_date_range(
        self,
        start_date: str,
        end_date: str,
        tags_filter: Optional[str] = None,
        order_mode: str = "date",
        include_completed: bool = False,
    ) -> List[Dict[str, Any]]:
        """Fetch tasks in a date range, including week-only tasks intersecting that range."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            start_week = self._week_sunday(start_date)
            end_week = self._week_sunday(end_date)

            query = '''
                SELECT
                    t.*,
                    r.title as record_title,
                    r.tags as record_tags,
                    r.type as record_type
                FROM tasks t
                LEFT JOIN records r ON t.record_id = r.id
                WHERE (
                    (t.day_date IS NOT NULL AND t.day_date BETWEEN ? AND ?)
                    OR (t.day_date IS NULL AND t.week_start BETWEEN ? AND ?)
                )
            '''
            params: List[Any] = [start_date, end_date, start_week, end_week]

            if not include_completed:
                query += " AND t.is_completed = 0"

            if tags_filter:
                tags = [t.strip() for t in str(tags_filter).split(",") if t and t.strip()]
                if tags:
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append("(COALESCE(r.tags, '') LIKE ? OR COALESCE(t.tags, '') LIKE ?)")
                        params.append(f"%{tag}%")
                        params.append(f"%{tag}%")
                    query += " AND (" + " OR ".join(tag_conditions) + ")"

            if order_mode == "custom":
                query += " ORDER BY COALESCE(t.custom_order, 999999999), t.created_at DESC, t.id DESC"
            else:
                query += " ORDER BY t.created_at DESC, t.id DESC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_tasks_by_week(self, week_start: str, tags_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all tasks for a specific week (Sunday date), optionally filtered by tags."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT
                    t.*,
                    r.title as record_title,
                    r.tags as record_tags,
                    r.type as record_type
                FROM tasks t
                LEFT JOIN records r ON t.record_id = r.id
                WHERE t.week_start = ?
            '''
            params = [week_start]
            if tags_filter:
                tags = [t.strip() for t in str(tags_filter).split(",") if t and t.strip()]
                if tags:
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append("(COALESCE(r.tags, '') LIKE ? OR COALESCE(t.tags, '') LIKE ?)")
                        params.append(f"%{tag}%")
                        params.append(f"%{tag}%")
                    query += " AND (" + " OR ".join(tag_conditions) + ")"
            query += " ORDER BY t.created_at ASC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_weekly_task_snapshot(self, week_start: str, tags_filter: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Return task groups for a week:
        - created_this_week: created between Monday and Sunday
        - completed_this_week: completed between Monday and Sunday
        - pending_from_before: created before Monday and still pending
        """
        week_end = datetime.strptime(week_start, "%Y-%m-%d").date()
        week_begin = week_end - timedelta(days=6)
        monday = week_begin.isoformat()
        sunday = week_end.isoformat()

        base_select = '''
            SELECT
                t.*,
                r.title AS record_title,
                r.tags AS record_tags,
                r.type AS record_type
            FROM tasks t
            LEFT JOIN records r ON t.record_id = r.id
        '''

        def _append_tags_filter(query: str, params: List[Any]) -> str:
            if not tags_filter:
                return query
            tags = [t.strip() for t in str(tags_filter).split(",") if t and t.strip()]
            if not tags:
                return query
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("(COALESCE(r.tags, '') LIKE ? OR COALESCE(t.tags, '') LIKE ?)")
                params.append(f"%{tag}%")
                params.append(f"%{tag}%")
            return query + " AND (" + " OR ".join(tag_conditions) + ")"

        with self.get_connection() as conn:
            cursor = conn.cursor()

            created_query = base_select + " WHERE date(t.created_at) BETWEEN ? AND ?"
            created_params: List[Any] = [monday, sunday]
            created_query = _append_tags_filter(created_query, created_params)
            created_query += " ORDER BY t.created_at DESC, t.id DESC"
            cursor.execute(created_query, created_params)
            created_this_week = [dict(row) for row in cursor.fetchall()]

            completed_query = base_select + " WHERE t.is_completed = 1 AND t.completed_at IS NOT NULL AND date(t.completed_at) BETWEEN ? AND ?"
            completed_params: List[Any] = [monday, sunday]
            completed_query = _append_tags_filter(completed_query, completed_params)
            completed_query += " ORDER BY t.completed_at DESC, t.id DESC"
            cursor.execute(completed_query, completed_params)
            completed_this_week = [dict(row) for row in cursor.fetchall()]

            pending_query = base_select + " WHERE t.is_completed = 0 AND date(t.created_at) < ?"
            pending_params: List[Any] = [monday]
            pending_query = _append_tags_filter(pending_query, pending_params)
            pending_query += " ORDER BY t.created_at DESC, t.id DESC"
            cursor.execute(pending_query, pending_params)
            pending_from_before = [dict(row) for row in cursor.fetchall()]

        return {
            "created_this_week": created_this_week,
            "completed_this_week": completed_this_week,
            "pending_from_before": pending_from_before,
        }

    def get_daily_task_snapshot(self, day_date: str, tags_filter: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Return task groups for a day:
        - created_this_day: tasks created on this date
        - completed_this_day: tasks completed on this date
        """
        base_select = '''
            SELECT
                t.*,
                r.title AS record_title,
                r.tags AS record_tags,
                r.type AS record_type
            FROM tasks t
            LEFT JOIN records r ON t.record_id = r.id
        '''

        def _append_tags_filter(query: str, params: List[Any]) -> str:
            if not tags_filter:
                return query
            tags = [t.strip() for t in str(tags_filter).split(",") if t and t.strip()]
            if not tags:
                return query
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("(COALESCE(r.tags, '') LIKE ? OR COALESCE(t.tags, '') LIKE ?)")
                params.append(f"%{tag}%")
                params.append(f"%{tag}%")
            return query + " AND (" + " OR ".join(tag_conditions) + ")"

        with self.get_connection() as conn:
            cursor = conn.cursor()

            created_query = base_select + " WHERE date(t.created_at) = ?"
            created_params: List[Any] = [day_date]
            created_query = _append_tags_filter(created_query, created_params)
            created_query += " ORDER BY t.created_at DESC, t.id DESC"
            cursor.execute(created_query, created_params)
            created_this_day = [dict(row) for row in cursor.fetchall()]

            completed_query = base_select + " WHERE t.is_completed = 1 AND t.completed_at IS NOT NULL AND date(t.completed_at) = ?"
            completed_params: List[Any] = [day_date]
            completed_query = _append_tags_filter(completed_query, completed_params)
            completed_query += " ORDER BY t.completed_at DESC, t.id DESC"
            cursor.execute(completed_query, completed_params)
            completed_this_day = [dict(row) for row in cursor.fetchall()]

        return {
            "created_this_day": created_this_day,
            "completed_this_day": completed_this_day,
        }

    def get_recent_incomplete_tasks(self, limit: Optional[int] = 20) -> List[Dict[str, Any]]:
        """Fetch latest incomplete tasks globally, newest first."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT
                    t.*,
                    r.title AS record_title,
                    r.tags AS record_tags,
                    r.created_at AS record_created_at
                FROM tasks t
                LEFT JOIN records r ON t.record_id = r.id
                WHERE t.is_completed = 0
                ORDER BY t.created_at DESC, t.id DESC
            '''
            params = []
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_tasks_for_board(self, order_mode: str = "date", include_completed: bool = False, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch tasks with metadata for the Tasks tab."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT
                    t.*,
                    r.title AS record_title,
                    r.tags AS record_tags,
                    r.created_at AS record_created_at
                FROM tasks t
                LEFT JOIN records r ON t.record_id = r.id
            '''
            params = []
            conditions = []
            if not include_completed:
                conditions.append("t.is_completed = 0")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            if order_mode == "custom":
                query += " ORDER BY COALESCE(t.custom_order, 999999999), t.created_at DESC, t.id DESC"
            else:
                query += " ORDER BY t.created_at DESC, t.id DESC"

            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def set_tasks_custom_order(self, ordered_task_ids: List[int]) -> None:
        """Persist custom order for tasks based on provided task IDs."""
        if not ordered_task_ids:
            return
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for idx, task_id in enumerate(ordered_task_ids, start=1):
                cursor.execute('UPDATE tasks SET custom_order = ? WHERE id = ?', (float(idx), task_id))
            conn.commit()

    def toggle_task_completion(self, task_id: int, is_completed: bool) -> None:
        """Toggle the completion status of a task."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if is_completed:
                completed_at = datetime.now().isoformat(sep=' ', timespec='seconds')
                cursor.execute(
                    'UPDATE tasks SET is_completed = 1, completed_at = ? WHERE id = ?',
                    (completed_at, task_id)
                )
            else:
                cursor.execute(
                    'UPDATE tasks SET is_completed = 0, completed_at = NULL WHERE id = ?',
                    (task_id,)
                )
            conn.commit()
