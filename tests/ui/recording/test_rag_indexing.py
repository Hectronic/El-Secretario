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
# along with this program.  See <https://www.gnu.org/licenses/>.

from unittest.mock import MagicMock

from src.ui.recording.rag_indexing import (
    SKIPPED_STATUS,
    index_saved_record_changes,
    index_transcription_result_after_refresh,
    should_auto_index_rag,
)


class FakeSettings:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def value(self, key, default=None, type=None):
        assert key == "auto_index_rag"
        if type is bool:
            return bool(self.enabled)
        return self.enabled if self.enabled is not None else default


def test_should_auto_index_rag_reads_bool_setting():
    assert should_auto_index_rag(FakeSettings(True)) is True
    assert should_auto_index_rag(FakeSettings(False)) is False


def test_index_transcription_result_after_refresh_adds_record_ai_text():
    db = MagicMock()
    db.get_record_ai_text.return_value = "Transcript plus notes"
    rag = MagicMock()
    statuses = []

    indexed = index_transcription_result_after_refresh(
        rag=rag,
        db=db,
        settings=FakeSettings(True),
        record_id=7,
        title="call.wav",
        date_label="2026-06-03",
        emit_status=statuses.append,
    )

    assert indexed is True
    db.get_record_ai_text.assert_called_once_with(7)
    rag.add_document.assert_called_once_with(
        7,
        "Transcript plus notes",
        {"title": "call.wav", "date": "2026-06-03"},
    )
    assert statuses == []


def test_index_transcription_result_after_refresh_emits_skip_status_when_disabled():
    db = MagicMock()
    rag = MagicMock()
    statuses = []

    indexed = index_transcription_result_after_refresh(
        rag=rag,
        db=db,
        settings=FakeSettings(False),
        record_id=7,
        title="call.wav",
        date_label="2026-06-03",
        emit_status=statuses.append,
    )

    assert indexed is False
    assert statuses == [SKIPPED_STATUS]
    db.get_record_ai_text.assert_not_called()
    rag.add_document.assert_not_called()


def test_index_transcription_result_after_refresh_noops_without_rag():
    db = MagicMock()
    statuses = []

    indexed = index_transcription_result_after_refresh(
        rag=None,
        db=db,
        settings=FakeSettings(True),
        record_id=7,
        title="call.wav",
        date_label="2026-06-03",
        emit_status=statuses.append,
    )

    assert indexed is False
    assert statuses == []
    db.get_record_ai_text.assert_not_called()


def test_index_saved_record_changes_composes_text_and_adds_metadata():
    db = MagicMock()
    db.compose_ai_text.return_value = "Composed"
    rag = MagicMock()

    indexed = index_saved_record_changes(
        rag=rag,
        db=db,
        settings=FakeSettings(True),
        record_id=9,
        transcription="Transcript",
        notes="Notes",
        title="Weekly",
        date_label="2026-06-03",
        tags="ops, ai",
    )

    assert indexed is True
    db.compose_ai_text.assert_called_once_with("Transcript", "Notes")
    rag.add_document.assert_called_once_with(
        9,
        "Composed",
        {"title": "Weekly", "date": "2026-06-03", "tags": "ops, ai"},
    )


def test_index_saved_record_changes_noops_when_disabled_or_missing_rag():
    db = MagicMock()
    rag = MagicMock()

    assert index_saved_record_changes(
        rag=rag,
        db=db,
        settings=FakeSettings(False),
        record_id=9,
        transcription="Transcript",
        notes="Notes",
        title="Weekly",
        date_label="2026-06-03",
        tags="ops",
    ) is False
    assert index_saved_record_changes(
        rag=None,
        db=db,
        settings=FakeSettings(True),
        record_id=9,
        transcription="Transcript",
        notes="Notes",
        title="Weekly",
        date_label="2026-06-03",
        tags="ops",
    ) is False
    db.compose_ai_text.assert_not_called()
    rag.add_document.assert_not_called()
