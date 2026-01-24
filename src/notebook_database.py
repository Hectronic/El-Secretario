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
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

class NotebookDBManager:
    def __init__(self, db_name: str = "notebooks.db"):
        self.db_name = db_name
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_name)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Notebooks Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notebooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Entries Table (for both text and audio notes)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notebook_id INTEGER NOT NULL,
                    type TEXT NOT NULL, -- 'text' or 'audio'
                    content TEXT, -- Text body or Transcription
                    title TEXT,
                    file_path TEXT, -- For audio files
                    duration REAL, -- For audio files
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
                )
            ''')
            conn.commit()

    def create_notebook(self, name: str, description: str = "") -> int:
        """Create a new notebook."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO notebooks (name, description) VALUES (?, ?)', (name, description))
            conn.commit()
            return cursor.lastrowid

    def get_notebooks(self) -> List[Dict[str, Any]]:
        """Fetch all notebooks."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM notebooks ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def get_notebook(self, notebook_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a specific notebook."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM notebooks WHERE id = ?', (notebook_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_notebook(self, notebook_id: int) -> None:
        """Delete a notebook and all its entries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM notebooks WHERE id = ?', (notebook_id,))
            conn.commit()

    def add_text_entry(self, notebook_id: int, content: str, title: str = "") -> int:
        """Add a text entry to a notebook."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO entries (notebook_id, type, content, title)
                VALUES (?, 'text', ?, ?)
            ''', (notebook_id, content, title))
            conn.commit()
            return cursor.lastrowid

    def add_audio_entry(self, notebook_id: int, file_path: str, duration: float, title: str = "") -> int:
        """Add an audio entry to a notebook."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO entries (notebook_id, type, file_path, duration, title, content)
                VALUES (?, 'audio', ?, ?, ?, 'Transcribing...')
            ''', (notebook_id, file_path, duration, title))
            conn.commit()
            return cursor.lastrowid

    def get_entries(self, notebook_id: int) -> List[Dict[str, Any]]:
        """Fetch all entries for a notebook."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM entries WHERE notebook_id = ? ORDER BY created_at DESC', (notebook_id,))
            return [dict(row) for row in cursor.fetchall()]

    def update_entry_content(self, entry_id: int, content: str) -> None:
        """Update content of an entry (e.g., after transcription or editing)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE entries SET content = ? WHERE id = ?', (content, entry_id))
            conn.commit()

    def delete_entry(self, entry_id: int) -> Optional[str]:
        """Delete an entry and return file_path if it was audio."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT file_path, type FROM entries WHERE id = ?', (entry_id,))
            row = cursor.fetchone()
            file_path = row['file_path'] if row and row['type'] == 'audio' else None
            
            cursor.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
            conn.commit()
            return file_path

    def rename_notebook(self, notebook_id: int, new_name: str) -> None:
        """Rename a notebook."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE notebooks SET name = ? WHERE id = ?', (new_name, notebook_id))
            conn.commit()

    def rename_entry(self, entry_id: int, new_title: str) -> None:
        """Rename an entry."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE entries SET title = ? WHERE id = ?', (new_title, entry_id))
            conn.commit()
