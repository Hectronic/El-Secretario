# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

from unittest.mock import MagicMock

from PyQt6.QtCore import QDate

from src.ui.chat.context_builder import build_chat_context_text, build_chat_session_contexts


class _Panel:
    def __init__(self):
        self.current_week_monday = None
        self.current_date_filter = None
        self._tags = []
        self._notebooks = []

    def get_active_notebooks(self):
        return list(self._notebooks)

    def get_active_tags(self):
        return list(self._tags)


def test_build_chat_context_text_includes_notebooks_records_tasks_and_rag():
    db = MagicMock()
    notebook_db = MagicMock()
    rag = MagicMock()
    panel = _Panel()
    panel._notebooks = [1]
    panel._tags = ["ops"]
    panel.current_week_monday = QDate(2026, 3, 9)
    panel.current_date_filter = "2026-03-15"
    db.fetch_record.return_value = {
        "id": 9,
        "title": "Pinned",
        "created_at": "2026-03-10",
        "transcription": "Transcript",
        "recording_notes": "Notes",
        "type": "recording",
    }
    db.fetch_by_date_range.return_value = [
        {
            "id": 9,
            "title": "Pinned",
            "created_at": "2026-03-10",
            "transcription": "Transcript",
            "recording_notes": "Notes",
            "type": "recording",
        }
    ]
    db.get_tasks_by_date_range.return_value = [{"content": "Task", "is_completed": 0, "task_origin": "Pinned"}]
    db.compose_ai_text.return_value = "Composed"
    notebook_db.get_entries.return_value = [{"content": "Notebook content", "title": "Notebook title"}]
    rag.search.return_value = [{"metadata": {"title": "Hit"}, "text": "Fragment"}]

    text = build_chat_context_text(db, notebook_db, rag, "query", panel, {9})

    assert "Notebook content" in text
    assert "Composed" in text
    assert "[Tasks]" in text
    assert "Fragment" in text
    assert db.fetch_by_date_range.called
    assert rag.search.called


def test_build_chat_session_contexts_serializes_current_selection():
    panel = _Panel()
    panel.current_week_monday = QDate(2026, 3, 9)
    panel.current_date_filter = "2026-03-15"
    panel._tags = ["ops"]
    panel._notebooks = [1, 2]

    result = build_chat_session_contexts(panel, {7})

    assert {"type": "date_range", "value": {"start": "2026-03-09", "end": "2026-03-15"}} in result
    assert {"type": "tag", "value": "ops"} in result
    assert {"type": "notebook", "value": 1} in result
    assert {"type": "recording", "value": 7} in result
