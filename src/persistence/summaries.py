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

from typing import Any, Dict, List, Optional



class SummariesRepository:
    def save_daily_summary(self, date: str, summary: str, tags_filter: Optional[str] = None) -> int:
        """
        Save or update a daily summary.

        Args:
            date: Date string in 'YYYY-MM-DD' format.
            summary: The summary text.
            tags_filter: Comma-separated tags used for filtering (None = no filter).

        Returns:
            The summary ID.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Set time to 23:59:59 of the given date
            now = f"{date} 23:59:59"
            # Use empty string instead of NULL for tags_filter to make UNIQUE constraint work
            tags_value = tags_filter if tags_filter else ''

            cursor.execute('''
                INSERT INTO daily_summaries (date, summary, tags_filter, generated_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date, tags_filter) DO UPDATE SET
                    summary = excluded.summary,
                    updated_at = excluded.updated_at
            ''', (date, summary, tags_value, now, now))
            conn.commit()
            return cursor.lastrowid

    def get_daily_summary(self, date: str, tags_filter: Optional[str] = None) -> Optional[str]:
        """
        Get a daily summary.

        Args:
            date: Date string in 'YYYY-MM-DD' format.
            tags_filter: Tags filter to match (None = no filter).

        Returns:
            The summary text if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_value = tags_filter if tags_filter else ''
            cursor.execute(
                'SELECT summary FROM daily_summaries WHERE date = ? AND tags_filter = ?',
                (date, tags_value)
            )
            row = cursor.fetchone()
            return row['summary'] if row else None

    def get_daily_summary_details(self, date: str, tags_filter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get full daily summary details.

        Args:
            date: Date string in 'YYYY-MM-DD' format.
            tags_filter: Tags filter to match (None = no filter).

        Returns:
            The summary dict if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_value = tags_filter if tags_filter else ''
            cursor.execute(
                'SELECT * FROM daily_summaries WHERE date = ? AND tags_filter = ?',
                (date, tags_value)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_latest_recording_day_without_daily_summary(
        self,
        before_date: str,
        tags_filter: Optional[str] = None,
    ) -> Optional[str]:
        """
        Return the latest day before `before_date` that has recordings and lacks daily summary.
        """
        tags_value = tags_filter if tags_filter else ''
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT date(r.created_at) AS day
                FROM records r
                WHERE r.type = 'recording' AND date(r.created_at) < ?
                GROUP BY date(r.created_at)
                HAVING NOT EXISTS (
                    SELECT 1
                    FROM daily_summaries ds
                    WHERE ds.date = day AND ds.tags_filter = ?
                )
                ORDER BY day DESC
                LIMIT 1
                ''',
                (before_date, tags_value),
            )
            row = cursor.fetchone()
            return row["day"] if row else None

    def save_weekly_summary(self, week_date: str, summary: str, tags_filter: Optional[str] = None) -> int:
        """
        Save or update a weekly summary.

        Args:
            week_date: Sunday of the week in 'YYYY-MM-DD' format.
            summary: The summary text.
            tags_filter: Comma-separated tags used for filtering (None = no filter).

        Returns:
            The summary ID.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Set time to 23:59:59 of the week date
            now = f"{week_date} 23:59:59"
            # Use empty string instead of NULL for tags_filter to make UNIQUE constraint work
            tags_value = tags_filter if tags_filter else ''

            cursor.execute('''
                INSERT INTO weekly_summaries (week_start, summary, tags_filter, generated_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(week_start, tags_filter) DO UPDATE SET
                    summary = excluded.summary,
                    updated_at = excluded.updated_at
            ''', (week_date, summary, tags_value, now, now))
            conn.commit()
            return cursor.lastrowid

    def get_weekly_summary(self, week_date: str, tags_filter: Optional[str] = None) -> Optional[str]:
        """
        Get a weekly summary.

        Args:
            week_date: Sunday of the week in 'YYYY-MM-DD' format.
            tags_filter: Tags filter to match (None = no filter).

        Returns:
            The summary text if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_value = tags_filter if tags_filter else ''
            cursor.execute(
                'SELECT summary FROM weekly_summaries WHERE week_start = ? AND tags_filter = ?',
                (week_date, tags_value)
            )
            row = cursor.fetchone()
            return row['summary'] if row else None

    def get_records_without_summary(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get recordings that have transcription but no summary.

        Args:
            limit: Optional limit on number of records to return.

        Returns:
            List of record dictionaries.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT * FROM records
                WHERE (
                    (transcription IS NOT NULL AND transcription != '')
                    OR (recording_notes IS NOT NULL AND recording_notes != '')
                )
                AND (summary IS NULL OR summary = '')
                ORDER BY created_at DESC
            '''
            params = []
            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_records_without_tasks(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get recordings that have transcription but no tasks in the tasks table.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT * FROM records
                WHERE (
                    (transcription IS NOT NULL AND transcription != '')
                    OR (recording_notes IS NOT NULL AND recording_notes != '')
                )
                AND NOT EXISTS (
                    SELECT 1 FROM tasks t WHERE t.record_id = records.id
                )
                ORDER BY created_at DESC
            '''
            params = []
            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_daily_summary(self, date: str, tags_filter: Optional[str] = None) -> Optional[str]:
        """
        Get a daily summary.

        Args:
            date: Date string in 'YYYY-MM-DD' format.
            tags_filter: Tags filter to match (None = no filter).

        Returns:
            The summary text if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_value = tags_filter if tags_filter else ''
            cursor.execute(
                'SELECT summary FROM daily_summaries WHERE date = ? AND tags_filter = ?',
                (date, tags_value)
            )
            row = cursor.fetchone()
            return row['summary'] if row else None

    def get_dates_with_content(self) -> List[str]:
        """
        Get all dates that have at least one recording.

        Returns:
            List of date strings in 'YYYY-MM-DD' format.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT date(created_at) as record_date
                FROM records
                WHERE (
                    (transcription IS NOT NULL AND transcription != '')
                    OR (recording_notes IS NOT NULL AND recording_notes != '')
                )
                ORDER BY record_date DESC
            ''')
            return [row['record_date'] for row in cursor.fetchall()]

    def get_weeks_with_content(self) -> List[str]:
        """
        Get all week end dates (Sundays) that have at least one recording.

        Returns:
            List of Sunday date strings in 'YYYY-MM-DD' format.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # SQLite: date(..., 'weekday 0') returns the next Sunday (or same day if Sunday)
            cursor.execute('''
                SELECT DISTINCT
                    date(created_at, 'weekday 0') as week_sunday
                FROM records
                WHERE (
                    (transcription IS NOT NULL AND transcription != '')
                    OR (recording_notes IS NOT NULL AND recording_notes != '')
                )
                ORDER BY week_sunday DESC
            ''')
            return [row['week_sunday'] for row in cursor.fetchall()]

    def get_dates_without_summary(self, tags_filter: Optional[str] = None, exclude_today: bool = False) -> List[str]:
        """
        Get dates with content but without a summary.

        Args:
            tags_filter: Tags filter to check against (None = no filter).
            exclude_today: If True, exclude the current date.

        Returns:
            List of date strings in 'YYYY-MM-DD' format.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_value = tags_filter if tags_filter else ''

            query = '''
                SELECT DISTINCT date(created_at) as record_date
                FROM records
                WHERE (
                    (transcription IS NOT NULL AND transcription != '')
                    OR (recording_notes IS NOT NULL AND recording_notes != '')
                )
                AND date(created_at) NOT IN (
                    SELECT date FROM daily_summaries WHERE tags_filter = ?
                )
            '''
            params = [tags_value]

            if exclude_today:
                query += " AND date(created_at) != date('now', 'localtime')"

            query += " ORDER BY record_date DESC"

            cursor.execute(query, params)
            return [row['record_date'] for row in cursor.fetchall()]

    def fetch_daily_summaries_by_range(self, start_date: str, end_date: str, tags_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch daily summaries within a date range.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_value = tags_filter if tags_filter else ''
            cursor.execute(
                'SELECT * FROM daily_summaries WHERE date >= ? AND date <= ? AND tags_filter = ? ORDER BY date DESC',
                (start_date, end_date, tags_value)
            )
            return [dict(row) for row in cursor.fetchall()]

    def fetch_daily_summaries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch all daily summaries ordered by date descending.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM daily_summaries ORDER BY date DESC"
            params = []
            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def fetch_weekly_summaries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch all weekly summaries ordered by week date descending.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM weekly_summaries ORDER BY week_start DESC"
            params = []
            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_weeks_without_summary(self, tags_filter: Optional[str] = None, exclude_current_week: bool = False) -> List[str]:
        """
        Get weeks with content but without a summary.

        Args:
            tags_filter: Tags filter to check against (None = no filter).
            exclude_current_week: If True, exclude the current week.

        Returns:
            List of Sunday date strings in 'YYYY-MM-DD' format.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_value = tags_filter if tags_filter else ''

            query = '''
                SELECT DISTINCT
                    date(created_at, 'weekday 0') as week_sunday
                FROM records
                WHERE (
                    (transcription IS NOT NULL AND transcription != '')
                    OR (recording_notes IS NOT NULL AND recording_notes != '')
                )
                AND date(created_at, 'weekday 0') NOT IN (
                    SELECT week_start FROM weekly_summaries WHERE tags_filter = ?
                )
            '''
            params = [tags_value]

            if exclude_current_week:
                # Calculate current week's sunday
                query += " AND date(created_at, 'weekday 0') != date('now', 'weekday 0')"

            query += " ORDER BY week_sunday DESC"

            cursor.execute(query, params)
            return [row['week_sunday'] for row in cursor.fetchall()]

    def get_dates_with_summary(self, tags_filter: Optional[str] = None) -> List[str]:
        """
        Get all dates that have a summary generated.

        Args:
            tags_filter: Tags filter to check against (None = no filter).

        Returns:
            List of date strings in 'YYYY-MM-DD' format.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_value = tags_filter if tags_filter else ''
            cursor.execute(
                'SELECT date FROM daily_summaries WHERE tags_filter = ? ORDER BY date DESC',
                (tags_value,)
            )
            return [row['date'] for row in cursor.fetchall()]

    def get_weeks_with_summary(self, tags_filter: Optional[str] = None) -> List[str]:
        """
        Get all weeks that have a summary generated.

        Args:
            tags_filter: Tags filter to check against (None = no filter).

        Returns:
            List of Sunday date strings in 'YYYY-MM-DD' format.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tags_value = tags_filter if tags_filter else ''
            cursor.execute(
                'SELECT week_start FROM weekly_summaries WHERE tags_filter = ? ORDER BY week_start DESC',
                (tags_value,)
            )
            return [row['week_start'] for row in cursor.fetchall()]

    # =========================================================================
    # TASK METHODS
    # =========================================================================
