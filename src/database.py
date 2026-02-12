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

import sqlite3
from datetime import datetime
import os
from contextlib import contextmanager
import re
from typing import List, Dict, Any, Optional, Union

class DBManager:
    def __init__(self, db_name: str = "transcriptions.db"):
        self.db_name = db_name
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_name)
        # Use Row factory for easier access by default
        conn.row_factory = sqlite3.Row 
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize the database and create the table if it doesn't exist."""
        import logging
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS records (
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
            
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        collection TEXT,
                        messages TEXT,
                        filter_date TEXT,
                        filter_tags TEXT,
                        context_data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transcription_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        model_name TEXT,
                        audio_duration REAL,
                        audio_size_bytes INTEGER,
                        transcription_time_seconds REAL,
                        record_id INTEGER,
                        FOREIGN KEY(record_id) REFERENCES records(id)
                    )
                ''')

                # Daily summaries table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        tags_filter TEXT,
                        generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(date, tags_filter)
                    )
                ''')

                # Weekly summaries table
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
                
                # Migration: Add columns if they don't exist
                cursor.execute("PRAGMA table_info(records)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'title' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN title TEXT')
                if 'summary' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN summary TEXT')
                if 'cleaned_text' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN cleaned_text TEXT')
                if 'is_favorite' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN is_favorite INTEGER DEFAULT 0')
                if 'is_diarized' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN is_diarized INTEGER DEFAULT 0')
                if 'transcription_model' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN transcription_model TEXT')
                if 'processing_attempts' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN processing_attempts INTEGER DEFAULT 0')
                if 'last_error' not in columns:
                    cursor.execute('ALTER TABLE records ADD COLUMN last_error TEXT')
                
                # Migration for chat_sessions
                cursor.execute("PRAGMA table_info(chat_sessions)")
                chat_columns = [column[1] for column in cursor.fetchall()]
                if 'filter_date' not in chat_columns:
                    cursor.execute('ALTER TABLE chat_sessions ADD COLUMN filter_date TEXT')
                if 'filter_tags' not in chat_columns:
                    cursor.execute('ALTER TABLE chat_sessions ADD COLUMN filter_tags TEXT')
                if 'context_data' not in chat_columns:
                    cursor.execute('ALTER TABLE chat_sessions ADD COLUMN context_data TEXT')
                    
                # Migration: Update existing summaries to have 23:59:59 timestamp
                # Ensures they appear after recordings for the day when sorted by time (if applicable)
                # or just meets user requirement.
                cursor.execute("UPDATE daily_summaries SET generated_at = date || ' 23:59:59' WHERE generated_at NOT LIKE '%23:59:59'")
                
                # Migration: Update existing weekly summaries from Monday to Sunday
                # strftime('%w', week_start) returns '1' for Monday.
                cursor.execute("UPDATE weekly_summaries SET week_start = date(week_start, '+6 days') WHERE strftime('%w', week_start) = '1'")
                
                cursor.execute("UPDATE weekly_summaries SET generated_at = week_start || ' 23:59:59' WHERE generated_at NOT LIKE '%23:59:59'")

                conn.commit()
            logging.info(f"Database initialized: {self.db_name}")
        except Exception as e:
            logging.critical(f"Database initialization failed: {e}", exc_info=True)
            raise

    def log_transcription(self, model_name: str, audio_duration: float, audio_size_bytes: int, transcription_time_seconds: float, record_id: int) -> None:
        """Log a transcription event."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            created_at = datetime.now().isoformat(sep=' ', timespec='seconds')
            cursor.execute('''
                INSERT INTO transcription_logs (created_at, model_name, audio_duration, audio_size_bytes, transcription_time_seconds, record_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (created_at, model_name, audio_duration, audio_size_bytes, transcription_time_seconds, record_id))
            conn.commit()

    def save(self, filename: str, text: str, duration: float, title: Optional[str] = None, is_diarized: bool = False, transcription_model: Optional[str] = None) -> int:
        """Save a new recording record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            created_at = datetime.now().isoformat(sep=' ', timespec='seconds')
            cursor.execute('''
                INSERT INTO records (created_at, filename, duration, transcription, title, is_diarized, transcription_model)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (created_at, filename, duration, text, title, 1 if is_diarized else 0, transcription_model))
            conn.commit()
            return cursor.lastrowid

    def fetch_pending_diarization(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch records that have not been diarized yet, ordered by creation date descending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM records WHERE is_diarized = 0 ORDER BY created_at DESC"
            params = []
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def fetch_diarized_records(self) -> List[Dict[str, Any]]:
        """Fetch all records that have been diarized."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM records WHERE is_diarized = 1 ORDER BY created_at DESC"
            cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def fetch_all(self, tag_filter: Optional[str] = None, favorites_only: bool = False) -> List[Dict[str, Any]]:
        """Fetch all records ordered by creation date descending, optionally filtered by tag and favorites."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM records WHERE 1=1"
            params = []
            
            if tag_filter and tag_filter != "All":
                query += " AND tags LIKE ?"
                params.append(f'%{tag_filter}%')
                
            if favorites_only:
                query += " AND is_favorite = 1"
                
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
                
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def fetch_by_date_range(self, start_date: str, end_date: str, tags: Optional[List[str]] = None, favorites_only: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch records within a date range (inclusive) and optionally filtered by tags.
        start_date, end_date: Strings in 'YYYY-MM-DD' format.
        tags: List of tags. If provided, record must have AT LEAST ONE of the tags.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM records WHERE date(created_at) BETWEEN ? AND ?"
            params = [start_date, end_date]
            
            if tags:
                # This is a simple OR filter for tags (contains any of the selected tags)
                # Since tags are stored as "tag1, tag2", we use LIKE for each
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append(f"%{tag}%")
                
                if tag_conditions:
                    query += " AND (" + " OR ".join(tag_conditions) + ")"
            
            if favorites_only:
                query += " AND is_favorite = 1"
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    def fetch_by_dates(self, dates: List[str], tags: Optional[List[str]] = None, favorites_only: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch records for specific dates and optionally filtered by tags.
        dates: List of strings in 'YYYY-MM-DD' format.
        tags: List of tags. If provided, record must have AT LEAST ONE of the tags.
        """
        if not dates:
            return []
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create placeholders for dates
            placeholders = ','.join(['?'] * len(dates))
            query = f"SELECT * FROM records WHERE date(created_at) IN ({placeholders})"
            params = list(dates)
            
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append(f"%{tag}%")
                
                if tag_conditions:
                    query += " AND (" + " OR ".join(tag_conditions) + ")"
            
            if favorites_only:
                query += " AND is_favorite = 1"
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def fetch_favorites(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """Fetch favorite records with pagination."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM records WHERE is_favorite = 1 ORDER BY created_at DESC"
            params = []
            
            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_tags(self) -> List[str]:
        """Return a sorted list of all unique tags."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT tags FROM records WHERE tags IS NOT NULL AND tags != ""')
            rows = cursor.fetchall()
            
            all_tags = set()
            for row in rows:
                tags = [t.strip() for t in row['tags'].split(',') if t.strip()]
                all_tags.update(tags)
                
            return sorted(list(all_tags))

    def get_all_speakers(self) -> List[str]:
        """Return a sorted list of all unique speaker names found in recent transcriptions."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Limit to last 50 records to be fast
            cursor.execute('SELECT transcription FROM records ORDER BY created_at DESC LIMIT 50')
            rows = cursor.fetchall()
            
            all_speakers = set()
            # Regex to find "Name: " pattern at start of line or after newline
            # Assuming format is "Name: Text..." or similar. 
            # Actually, based on previous context, speakers might be just replaced in text.
            # But if we want to autocomplete *names* that user has used before, we need to find them.
            # If the user renames "SPEAKER_00" to "Alice", the text becomes "Alice: Hello".
            # So we look for "Name:" pattern.
            pattern = re.compile(r'(?:^|\n)([^:\n]+):')
            
            for row in rows:
                text = row['transcription']
                if text:
                    matches = pattern.findall(text)
                    for match in matches:
                        name = match.strip()
                        # Filter out default SPEAKER_XX names and empty strings
                        if name and not re.match(r'^SPEAKER_\d+$', name):
                            all_speakers.add(name)
                            
            return sorted(list(all_speakers))

    def update_tags(self, record_id: int, tags: str) -> None:
        """Update the tags of a record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE records SET tags = ? WHERE id = ?', (tags, record_id))
            conn.commit()

    def update_title(self, record_id: int, title: str) -> None:
        """Update the title of a record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE records SET title = ? WHERE id = ?', (title, record_id))
            conn.commit()

    def update_duration(self, record_id: int, duration: float) -> None:
        """Update the duration of a record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE records SET duration = ? WHERE id = ?', (duration, record_id))
            conn.commit()

    def update_transcription(self, record_id: int, text: str, is_diarized: Optional[bool] = None, transcription_model: Optional[str] = None) -> None:
        """Update the transcription of a record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            fields = ["transcription = ?"]
            params = [text]
            
            if is_diarized is not None:
                fields.append("is_diarized = ?")
                params.append(1 if is_diarized else 0)
                
            if transcription_model is not None:
                fields.append("transcription_model = ?")
                params.append(transcription_model)
                
            params.append(record_id)
            
            query = f"UPDATE records SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()

    def update_ai_content(self, record_id: int, summary: Optional[str] = None, cleaned_text: Optional[str] = None) -> None:
        """Update AI generated content for a record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if summary:
                cursor.execute('UPDATE records SET summary = ? WHERE id = ?', (summary, record_id))
            if cleaned_text:
                cursor.execute('UPDATE records SET cleaned_text = ? WHERE id = ?', (cleaned_text, record_id))
            conn.commit()

    def toggle_favorite(self, record_id: int, is_favorite: bool) -> None:
        """Update the favorite status of a record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            val = 1 if is_favorite else 0
            cursor.execute('UPDATE records SET is_favorite = ? WHERE id = ?', (val, record_id))
            conn.commit()

    # Chat Session Methods
    def save_chat_session(self, name: str, collection: str, messages_json: str, filter_date: Optional[str] = None, filter_tags: Optional[str] = None, context_data: Optional[str] = None) -> int:
        """Save a new chat session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO chat_sessions (name, collection, messages, filter_date, filter_tags, context_data) VALUES (?, ?, ?, ?, ?, ?)',
                           (name, collection, messages_json, filter_date, filter_tags, context_data))
            conn.commit()
            return cursor.lastrowid

    def fetch_chat_sessions(self) -> List[Dict[str, Any]]:
        """Fetch all chat sessions ordered by date descending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM chat_sessions ORDER BY created_at DESC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_chat_session(self, session_id: int, messages_json: str, filter_date: Optional[str] = None, filter_tags: Optional[str] = None, context_data: Optional[str] = None) -> None:
        """Update messages and filters in an existing session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            fields = ["messages = ?"]
            params = [messages_json]
            
            if filter_date is not None:
                fields.append("filter_date = ?")
                params.append(filter_date)
            
            if filter_tags is not None:
                fields.append("filter_tags = ?")
                params.append(filter_tags)
                
            if context_data is not None:
                fields.append("context_data = ?")
                params.append(context_data)
                
            params.append(session_id)
            
            query = f"UPDATE chat_sessions SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()

    def delete_chat_session(self, session_id: int) -> None:
        """Delete a chat session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
            conn.commit()

    def delete(self, record_id: int) -> Optional[str]:
        """Delete a record by ID and return its filename."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Get filename first
            cursor.execute('SELECT filename FROM records WHERE id = ?', (record_id,))
            row = cursor.fetchone()
            filename = row['filename'] if row else None
            
            cursor.execute('DELETE FROM records WHERE id = ?', (record_id,))
            conn.commit()
            return filename

    def increment_attempt(self, record_id: int) -> int:
        """Increment the processing attempts count and return the new value."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE records SET processing_attempts = processing_attempts + 1 WHERE id = ?', (record_id,))
            conn.commit()
            
            cursor.execute('SELECT processing_attempts FROM records WHERE id = ?', (record_id,))
            return cursor.fetchone()[0]

    def set_error(self, record_id: int, error_message: str) -> None:
        """Set the last error message for a record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE records SET last_error = ? WHERE id = ?', (error_message, record_id))
            conn.commit()

    def reset_attempts(self, record_id: int) -> None:
        """Reset attempts and clear error message (for manual retry)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE records SET processing_attempts = 0, last_error = NULL WHERE id = ?', (record_id,))
            conn.commit()

    # =========================================================================
    # EXPORT/IMPORT METHODS
    # =========================================================================

    def fetch_transcription_logs(self) -> List[Dict[str, Any]]:
        """Fetch all transcription logs for export."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM transcription_logs ORDER BY created_at DESC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def record_exists_by_hash(self, created_at: str, content_hash: str) -> bool:
        """
        Check if a record already exists based on timestamp and content hash.
        
        Args:
            created_at: Record creation timestamp.
            content_hash: Hash of the transcription content.
            
        Returns:
            True if a matching record exists.
        """
        import hashlib
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # First check by created_at timestamp
            cursor.execute('SELECT transcription FROM records WHERE created_at = ?', (created_at,))
            rows = cursor.fetchall()
            
            for row in rows:
                transcription = row['transcription'] or ''
                existing_hash = hashlib.sha256(transcription.encode('utf-8')).hexdigest()
                if existing_hash == content_hash:
                    return True
            return False

    def chat_session_exists(self, name: str, created_at: str) -> bool:
        """
        Check if a chat session already exists based on name and timestamp.
        
        Args:
            name: Session name.
            created_at: Session creation timestamp.
            
        Returns:
            True if a matching session exists.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM chat_sessions WHERE name = ? AND created_at = ?', (name, created_at))
            return cursor.fetchone() is not None

    def import_record(self, record: Dict[str, Any]) -> Optional[int]:
        """
        Import a single record from export data.
        
        Args:
            record: Record dictionary with all fields.
            
        Returns:
            The new record ID, or None if import failed.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO records (
                    created_at, filename, duration, transcription, title, tags,
                    summary, cleaned_text, is_favorite, is_diarized, transcription_model,
                    processing_attempts, last_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('created_at'),
                record.get('filename', ''),
                record.get('duration', 0),
                record.get('transcription', ''),
                record.get('title'),
                record.get('tags'),
                record.get('summary'),
                record.get('cleaned_text'),
                record.get('is_favorite', 0),
                record.get('is_diarized', 0),
                record.get('transcription_model'),
                record.get('processing_attempts', 0),
                record.get('last_error')
            ))
            conn.commit()
            return cursor.lastrowid

    def import_chat_session(self, session: Dict[str, Any]) -> Optional[int]:
        """
        Import a single chat session from export data.
        
        Args:
            session: Chat session dictionary with all fields.
            
        Returns:
            The new session ID, or None if import failed.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_sessions (
                    name, collection, messages, filter_date, filter_tags, context_data, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.get('name'),
                session.get('collection'),
                session.get('messages'),
                session.get('filter_date'),
                session.get('filter_tags'),
                session.get('context_data'),
                session.get('created_at')
            ))
            conn.commit()
            return cursor.lastrowid

    # =========================================================================
    # DAILY/WEEKLY SUMMARY METHODS
    # =========================================================================

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
                WHERE transcription IS NOT NULL AND transcription != ''
                AND (summary IS NULL OR summary = '')
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
                WHERE transcription IS NOT NULL AND transcription != ''
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
                WHERE transcription IS NOT NULL AND transcription != ''
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
                WHERE transcription IS NOT NULL AND transcription != ''
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
                WHERE transcription IS NOT NULL AND transcription != ''
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
