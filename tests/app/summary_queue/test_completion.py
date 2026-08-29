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

from src.app.summary_queue.completion import (
    build_rag_reindex_status,
    handle_worker_completion,
    persist_task_extraction_result,
    should_chain_summary_after_transcription,
)
from src.database import DBManager


def test_should_chain_summary_after_transcription_skips_batch_process():
    assert should_chain_summary_after_transcription({"source": "manual"}) is True
    assert should_chain_summary_after_transcription({"source": "batch_process"}) is False


def test_build_rag_reindex_status_formats_scope_and_counts():
    assert build_rag_reindex_status(
        {"type": "rag_reindex", "reindex_scope": "missing"},
        {"indexed": 2, "skipped": 1, "total": 3},
    ) == "RAG reindex (missing only) completed: 2/3 indexed, 1 skipped."


def test_persist_task_extraction_result_replaces_ai_tasks(tmp_path):
    db = DBManager(str(tmp_path / "queue.sqlite"))
    record_id = db.save("rec.wav", "Transcript", 1.0, "Title")
    db.save_task(record_id=record_id, content="Old AI", tags="old", is_ai_generated=True)
    db.save_task(record_id=record_id, content="Manual", tags="manual", is_ai_generated=False)

    count = persist_task_extraction_result(
        db,
        {"type": "task_extraction", "record_id": record_id, "tags": "tag-a"},
        '["Task 1", "Task 2"]',
    )

    tasks = db.get_tasks_by_record(record_id)
    assert count == 2
    assert [task["content"] for task in tasks] == ["Manual", "Task 1", "Task 2"]
    assert tasks[1]["tags"] == "tag-a"
    assert tasks[1]["is_ai_generated"] == 1


def test_handle_summary_completion_persists_and_returns_task_extraction_action(tmp_path):
    db = DBManager(str(tmp_path / "queue.sqlite"))
    record_id = db.save("rec.wav", "Transcript", 1.0, "Title")
    db.update_tags(record_id, "work")

    actions = handle_worker_completion(
        db,
        {"type": "summary", "record_id": record_id, "source": "manual"},
        "Generated summary",
    )

    assert db.fetch_record(record_id)["summary"] == "Generated summary"
    assert actions == [
        {
            "type": "enqueue_task_extraction",
            "record_id": record_id,
            "text": "Transcript",
            "tags": "work",
            "title": "Title",
            "source": "manual",
        }
    ]


def test_handle_weekly_summary_completion_persists_without_actions(tmp_path):
    db = DBManager(str(tmp_path / "queue.sqlite"))

    actions = handle_worker_completion(
        db,
        {"type": "weekly_summary", "date": "2026-05-10", "tags_filter": "work"},
        "Weekly summary",
    )

    assert actions == []
    assert db.get_weekly_summary("2026-05-10", "work") == "Weekly summary"


def test_handle_transcription_completion_persists_and_returns_summary_action(tmp_path):
    db = DBManager(str(tmp_path / "queue.sqlite"))
    record_id = db.save("rec.wav", "", 1.0, "Title")

    actions = handle_worker_completion(
        db,
        {"type": "transcription", "record_id": record_id, "title": "Title", "source": "manual"},
        {"text": "Recognized", "model_name": "base", "is_diarized": True},
    )

    record = db.fetch_record(record_id)
    assert record["transcription"] == "Recognized"
    assert record["transcription_model"] == "base"
    assert record["is_diarized"] == 1
    assert actions == [
        {
            "type": "enqueue_recording_summary",
            "record_id": record_id,
            "text": "Recognized",
            "title": "Title",
            "source": "manual",
        }
    ]


def test_handle_transcription_completion_skips_batch_summary_action(tmp_path):
    db = DBManager(str(tmp_path / "queue.sqlite"))
    record_id = db.save("rec.wav", "", 1.0, "Title")

    actions = handle_worker_completion(
        db,
        {"type": "transcription", "record_id": record_id, "source": "batch_process"},
        {"text": "Recognized", "model_name": "base", "is_diarized": False},
    )

    assert actions == []


def test_handle_rag_reindex_completion_returns_status_action():
    assert handle_worker_completion(
        None,
        {"type": "rag_reindex", "reindex_scope": "all"},
        {"indexed": 1, "skipped": 0, "total": 1},
    ) == [
        {
            "type": "status",
            "message": "RAG reindex (all records) completed: 1/1 indexed, 0 skipped.",
        }
    ]
