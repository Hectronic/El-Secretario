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



class ChatSessionsRepository:
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
            cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()

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
