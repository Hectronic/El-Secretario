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

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional



class RecordsRepository:
    def save(self, filename: str, text: str, duration: float, title: Optional[str] = None, is_diarized: bool = False, transcription_model: Optional[str] = None, type: str = 'recording', recording_notes: Optional[str] = None) -> int:
        """Save a new record (recording or note)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            created_at = datetime.now().isoformat(sep=' ', timespec='seconds')
            cursor.execute('''
                INSERT INTO records (created_at, filename, duration, transcription, recording_notes, title, is_diarized, transcription_model, type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (created_at, filename, duration, text, recording_notes, title, 1 if is_diarized else 0, transcription_model, type))
            conn.commit()
            return cursor.lastrowid

    def save_note(self, title: str, content: str, tags: str = "") -> int:
        """Convenience method to save a note."""
        return self.save(filename="", text=content, duration=0.0, title=title, type='note')

    def fetch_pending_diarization(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch records that have not been diarized yet, ordered by creation date descending."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM records WHERE is_diarized = 0 AND type = 'recording' ORDER BY created_at DESC"
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
            query = "SELECT * FROM records WHERE is_diarized = 1 AND type = 'recording' ORDER BY created_at DESC"
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

    def fetch_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single record by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM records WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

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
            # Keep task tags in sync for tasks linked to this recording.
            cursor.execute('UPDATE tasks SET tags = ? WHERE record_id = ?', (tags, record_id))
            conn.commit()

    def update_title(self, record_id: int, title: str) -> None:
        """Update the title of a record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE records SET title = ? WHERE id = ?', (title, record_id))
            # Keep task origin in sync for tasks linked to this recording.
            cursor.execute('UPDATE tasks SET task_origin = ? WHERE record_id = ?', (title, record_id))
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

    def update_recording_notes(self, record_id: int, notes: str) -> None:
        """Update user notes associated with a recording."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE records SET recording_notes = ? WHERE id = ?', (notes, record_id))
            conn.commit()

    @staticmethod
    def compose_ai_text(transcription: Optional[str], recording_notes: Optional[str]) -> str:
        """Compose AI input text by merging transcription and user notes."""
        transcription_text = (transcription or "").strip()
        notes_text = (recording_notes or "").strip()

        if transcription_text and notes_text:
            return f"{transcription_text}\n\n[User notes]\n{notes_text}"
        if notes_text:
            return f"[User notes]\n{notes_text}"
        return transcription_text

    def get_record_ai_text(self, record_id: int) -> str:
        """Get composed AI input text for a record."""
        record = self.fetch_record(record_id)
        if not record:
            return ""
        return self.compose_ai_text(record.get("transcription"), record.get("recording_notes"))

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
            cursor.execute('SELECT transcription, recording_notes FROM records WHERE created_at = ?', (created_at,))
            rows = cursor.fetchall()

            for row in rows:
                transcription = row['transcription'] or ''
                recording_notes = row['recording_notes'] or ''
                combined_content = self.compose_ai_text(transcription, recording_notes)
                existing_hash = hashlib.sha256(combined_content.encode('utf-8')).hexdigest()
                if existing_hash == content_hash:
                    return True
            return False
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
                    created_at, filename, duration, transcription, recording_notes, title, tags,
                    summary, cleaned_text, is_favorite, is_diarized, transcription_model,
                    processing_attempts, last_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('created_at'),
                record.get('filename', ''),
                record.get('duration', 0),
                record.get('transcription', ''),
                record.get('recording_notes'),
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
