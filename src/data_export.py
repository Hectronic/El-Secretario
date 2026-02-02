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

"""
Data Export/Import Module for El Secretario.

Provides functionality to export all application data (records, chat sessions,
notebooks, transcription logs) to JSON format and import them back with
duplicate detection.
"""

import json
import hashlib
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

from src.database import DBManager
from src.notebook_database import NotebookDBManager


APP_NAME = "El Secretario"
APP_VERSION = "1.0.0"
EXPORT_FORMAT_VERSION = "1"


@dataclass
class ImportStats:
    """Statistics for a single data type import."""
    imported: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: List[str] = field(default_factory=list)


@dataclass
class ImportResult:
    """Complete import operation result."""
    records: ImportStats = field(default_factory=ImportStats)
    chat_sessions: ImportStats = field(default_factory=ImportStats)
    notebooks: ImportStats = field(default_factory=ImportStats)
    success: bool = True
    error_message: Optional[str] = None


class DataExporter:
    """Handles export/import of all application data."""

    def __init__(self, db: DBManager, notebook_db: NotebookDBManager):
        """
        Initialize the DataExporter.
        
        Args:
            db: Main database manager for records and chat sessions.
            notebook_db: Notebook database manager.
        """
        self.db = db
        self.notebook_db = notebook_db
        self.logger = logging.getLogger(__name__)

    # =========================================================================
    # EXPORT FUNCTIONS
    # =========================================================================

    def export_all(self, output_path: str) -> Dict[str, Any]:
        """
        Export all application data to a JSON file.
        
        Args:
            output_path: Path to save the export file.
            
        Returns:
            Dictionary with export metadata and statistics.
        """
        self.logger.info(f"Starting export to {output_path}")
        
        export_data = {
            "export_metadata": {
                "app_name": APP_NAME,
                "app_version": APP_VERSION,
                "export_date": datetime.now().isoformat(),
                "export_format_version": EXPORT_FORMAT_VERSION
            },
            "records": self.export_records(),
            "chat_sessions": self.export_chat_sessions(),
            "transcription_logs": self.export_transcription_logs(),
            "notebooks": self.export_notebooks()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        stats = {
            "records_count": len(export_data["records"]),
            "chat_sessions_count": len(export_data["chat_sessions"]),
            "transcription_logs_count": len(export_data["transcription_logs"]),
            "notebooks_count": len(export_data["notebooks"]),
            "output_path": output_path
        }
        
        self.logger.info(f"Export complete: {stats}")
        return stats

    def export_records(self) -> List[Dict[str, Any]]:
        """Export all records from the database."""
        records = self.db.fetch_all()
        # Add content hash for duplicate detection on import
        for record in records:
            record['_content_hash'] = self._compute_record_hash(record)
        return records

    def export_chat_sessions(self) -> List[Dict[str, Any]]:
        """Export all chat sessions from the database."""
        return self.db.fetch_chat_sessions()

    def export_transcription_logs(self) -> List[Dict[str, Any]]:
        """Export all transcription logs from the database."""
        return self.db.fetch_transcription_logs()

    def export_notebooks(self) -> List[Dict[str, Any]]:
        """Export all notebooks with their entries."""
        return self.notebook_db.get_all_notebooks_with_entries()

    # =========================================================================
    # IMPORT FUNCTIONS
    # =========================================================================

    def import_all(self, input_path: str) -> ImportResult:
        """
        Import all application data from a JSON file.
        
        Args:
            input_path: Path to the import file.
            
        Returns:
            ImportResult with statistics for each data type.
        """
        self.logger.info(f"Starting import from {input_path}")
        result = ImportResult()
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            result.success = False
            result.error_message = f"Failed to read import file: {e}"
            self.logger.error(result.error_message)
            return result

        # Validate format version
        metadata = import_data.get("export_metadata", {})
        format_version = metadata.get("export_format_version")
        if format_version != EXPORT_FORMAT_VERSION:
            self.logger.warning(f"Format version mismatch: {format_version} vs {EXPORT_FORMAT_VERSION}")

        # Import each data type
        if "records" in import_data:
            result.records = self.import_records(import_data["records"])
        
        if "chat_sessions" in import_data:
            result.chat_sessions = self.import_chat_sessions(import_data["chat_sessions"])
        
        if "notebooks" in import_data:
            result.notebooks = self.import_notebooks(import_data["notebooks"])

        self.logger.info(f"Import complete: records={asdict(result.records)}, "
                        f"sessions={asdict(result.chat_sessions)}, "
                        f"notebooks={asdict(result.notebooks)}")
        return result

    def import_records(self, records: List[Dict[str, Any]]) -> ImportStats:
        """
        Import records with duplicate detection.
        
        Args:
            records: List of record dictionaries to import.
            
        Returns:
            ImportStats with import statistics.
        """
        stats = ImportStats()
        
        for record in records:
            try:
                # Check for duplicate
                content_hash = record.get('_content_hash') or self._compute_record_hash(record)
                created_at = record.get('created_at', '')
                
                if self._record_exists(created_at, content_hash):
                    stats.skipped += 1
                    continue
                
                # Import the record
                record_id = self.db.import_record(record)
                if record_id:
                    stats.imported += 1
                else:
                    stats.skipped += 1
                    
            except Exception as e:
                stats.errors += 1
                stats.error_messages.append(str(e))
                self.logger.error(f"Error importing record: {e}")
        
        return stats

    def import_chat_sessions(self, sessions: List[Dict[str, Any]]) -> ImportStats:
        """
        Import chat sessions with duplicate detection.
        
        Args:
            sessions: List of chat session dictionaries to import.
            
        Returns:
            ImportStats with import statistics.
        """
        stats = ImportStats()
        
        for session in sessions:
            try:
                name = session.get('name', '')
                created_at = session.get('created_at', '')
                
                if self._chat_session_exists(name, created_at):
                    stats.skipped += 1
                    continue
                
                # Import the session
                session_id = self.db.import_chat_session(session)
                if session_id:
                    stats.imported += 1
                else:
                    stats.skipped += 1
                    
            except Exception as e:
                stats.errors += 1
                stats.error_messages.append(str(e))
                self.logger.error(f"Error importing chat session: {e}")
        
        return stats

    def import_notebooks(self, notebooks: List[Dict[str, Any]]) -> ImportStats:
        """
        Import notebooks with their entries and duplicate detection.
        
        Args:
            notebooks: List of notebook dictionaries with entries.
            
        Returns:
            ImportStats with import statistics.
        """
        stats = ImportStats()
        
        for notebook in notebooks:
            try:
                name = notebook.get('name', '')
                created_at = notebook.get('created_at', '')
                
                if self.notebook_db.notebook_exists(name, created_at):
                    stats.skipped += 1
                    continue
                
                # Import the notebook with entries
                notebook_id = self.notebook_db.import_notebook(notebook)
                if notebook_id:
                    stats.imported += 1
                else:
                    stats.skipped += 1
                    
            except Exception as e:
                stats.errors += 1
                stats.error_messages.append(str(e))
                self.logger.error(f"Error importing notebook: {e}")
        
        return stats

    # =========================================================================
    # DUPLICATE DETECTION HELPERS
    # =========================================================================

    def _compute_record_hash(self, record: Dict[str, Any]) -> str:
        """
        Compute a hash for a record based on its transcription content.
        
        Args:
            record: Record dictionary.
            
        Returns:
            SHA256 hash of the transcription content.
        """
        transcription = record.get('transcription', '') or ''
        return hashlib.sha256(transcription.encode('utf-8')).hexdigest()

    def _record_exists(self, created_at: str, content_hash: str) -> bool:
        """
        Check if a record already exists based on timestamp and content hash.
        
        Args:
            created_at: Record creation timestamp.
            content_hash: Hash of the transcription content.
            
        Returns:
            True if a matching record exists.
        """
        return self.db.record_exists_by_hash(created_at, content_hash)

    def _chat_session_exists(self, name: str, created_at: str) -> bool:
        """
        Check if a chat session already exists based on name and timestamp.
        
        Args:
            name: Session name.
            created_at: Session creation timestamp.
            
        Returns:
            True if a matching session exists.
        """
        return self.db.chat_session_exists(name, created_at)
