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
