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

from src.app.summary_queue.tasks import (
    build_daily_summary_task,
    build_rag_reindex_task,
    build_recording_summary_task,
    build_task_extraction_task,
    build_transcription_task,
    build_weekly_summary_task,
    normalize_source,
    task_key,
)


def test_normalize_source_strips_lowercases_and_uses_default():
    assert normalize_source(" Batch Process ") == "batch_process"
    assert normalize_source("", default="startup") == "startup"
    assert normalize_source(None) == "manual"


def test_task_key_matches_queue_deduplication_fields():
    task = {
        "type": "transcription",
        "date": "2026-05-11",
        "record_id": 12,
        "tags_filter": "work",
        "audio_path": "/tmp/audio.wav",
        "reindex_scope": "missing",
        "title": "Ignored",
    }

    assert task_key(task) == (
        "transcription",
        "2026-05-11",
        12,
        "work",
        "/tmp/audio.wav",
        "missing",
    )


def test_build_daily_summary_task_requires_date():
    assert build_daily_summary_task({"tags_filter": "work"}) is None
    assert build_daily_summary_task(
        {"date": "2026-05-11", "tags_filter": "work", "source": "Calendar"}
    ) == {
        "type": "daily_summary",
        "date": "2026-05-11",
        "tags_filter": "work",
        "source": "calendar",
    }


def test_build_recording_and_weekly_summary_tasks():
    assert build_recording_summary_task(7, "Text", "Title", source="Auto Chain") == {
        "type": "summary",
        "record_id": 7,
        "text": "Text",
        "title": "Title",
        "source": "auto_chain",
    }
    assert build_weekly_summary_task("2026-05-10", "Week text", "tag", source="startup") == {
        "type": "weekly_summary",
        "date": "2026-05-10",
        "text": "Week text",
        "tags_filter": "tag",
        "source": "startup",
    }


def test_build_task_extraction_task_resolves_title_and_force():
    assert build_task_extraction_task(5, "Text", "tag", "", force=True, source="summary") == {
        "type": "task_extraction",
        "record_id": 5,
        "text": "Text",
        "tags": "tag",
        "title": "Recording 5",
        "force": True,
        "source": "summary",
    }


def test_build_transcription_task_preserves_runtime_choices():
    assert build_transcription_task(
        3,
        "/tmp/audio.wav",
        model_size="large-v3",
        language="es",
        diarization=True,
        title="Audio",
        source="batch_process",
    ) == {
        "type": "transcription",
        "record_id": 3,
        "audio_path": "/tmp/audio.wav",
        "model_size": "large-v3",
        "language": "es",
        "diarization": True,
        "title": "Audio",
        "source": "batch_process",
    }


def test_build_rag_reindex_task_normalizes_scope():
    assert build_rag_reindex_task("missing", source="Settings") == {
        "type": "rag_reindex",
        "title": "RAG Reindex",
        "reindex_scope": "missing",
        "source": "settings",
    }
    assert build_rag_reindex_task("invalid")["reindex_scope"] == "all"

