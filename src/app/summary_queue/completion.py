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

from typing import Any, Dict, List

from src.app.summary_queue.helpers import parse_task_extraction_result


def should_chain_summary_after_transcription(task: Dict) -> bool:
    return task.get("source") != "batch_process"


def build_rag_reindex_status(task: Dict, result: Dict) -> str:
    indexed = int(result.get("indexed", 0))
    skipped = int(result.get("skipped", 0))
    total = int(result.get("total", 0))
    scope_label = "missing only" if task.get("reindex_scope") == "missing" else "all records"
    return f"RAG reindex ({scope_label}) completed: {indexed}/{total} indexed, {skipped} skipped."


def persist_task_extraction_result(db, task: Dict, result: Any) -> int:
    tasks = parse_task_extraction_result(result)
    if not tasks:
        return 0

    db.delete_ai_tasks_by_record(task["record_id"])
    for task_content in tasks:
        db.save_task(
            task["record_id"],
            task_content,
            task.get("tags"),
            is_ai_generated=True,
        )
    return len(tasks)


def persist_summary_result(db, task: Dict, result: Any) -> List[Dict]:
    db.update_ai_content(task["record_id"], summary=str(result))
    rec = db.fetch_record(task["record_id"])
    if not rec:
        return []

    return [
        {
            "type": "enqueue_task_extraction",
            "record_id": task["record_id"],
            "text": db.get_record_ai_text(task["record_id"]),
            "tags": rec.get("tags") or "",
            "title": rec.get("title") or f"Recording {task['record_id']}",
            "source": task.get("source") or "summary",
        }
    ]


def persist_weekly_summary_result(db, task: Dict, result: Any) -> List[Dict]:
    db.save_weekly_summary(task["date"], str(result), task.get("tags_filter"))
    return []


def persist_transcription_result(db, task: Dict, result: Dict) -> List[Dict]:
    text = result["text"]
    db.update_transcription(
        task["record_id"],
        text,
        is_diarized=result.get("is_diarized", False),
        transcription_model=result.get("model_name"),
    )
    if not should_chain_summary_after_transcription(task):
        return []

    return [
        {
            "type": "enqueue_recording_summary",
            "record_id": task["record_id"],
            "text": db.get_record_ai_text(task["record_id"]),
            "title": task.get("title", ""),
            "source": task.get("source") or "transcription",
        }
    ]


def handle_worker_completion(db, task: Dict, result: Any) -> List[Dict]:
    task_type = task.get("type")
    if task_type == "summary":
        return persist_summary_result(db, task, result)
    if task_type == "weekly_summary":
        return persist_weekly_summary_result(db, task, result)
    if task_type == "task_extraction":
        persist_task_extraction_result(db, task, result)
        return []
    if task_type == "transcription":
        return persist_transcription_result(db, task, result)
    if task_type == "rag_reindex" and isinstance(result, dict):
        return [{"type": "status", "message": build_rag_reindex_status(task, result)}]
    return []

