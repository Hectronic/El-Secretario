"""Task-admission policy for the sequential summary queue."""

from collections.abc import Callable
from typing import Any

from src.app.summary_queue.tasks import (
    build_daily_summary_task,
    build_rag_reindex_task,
    build_recording_summary_task,
    build_task_extraction_task,
    build_transcription_task,
    build_weekly_summary_task,
)


class QueueTaskAdmissionCoordinator:
    """Build, validate, and submit queue tasks without coupling to Qt."""

    def __init__(self, db: Any, *, submit: Callable[[dict], bool], skip: Callable[[dict, str], None]):
        self.db = db
        self._submit = submit
        self._skip = skip

    def enqueue_daily_summary(self, summary_data: dict) -> bool:
        task = build_daily_summary_task(summary_data)
        if task is None:
            self._skip(summary_data, "Daily summary task missing date.")
            return False
        return self._submit(task)

    def enqueue_recording_summary(self, record_id: int, text: str, title: str, source: str) -> bool:
        return self._submit(build_recording_summary_task(record_id, text, title, source))

    def enqueue_weekly_summary(self, week_sunday: str, text: str, tags_filter: str, source: str) -> bool:
        return self._submit(build_weekly_summary_task(week_sunday, text, tags_filter, source))

    def enqueue_task_extraction(self, record_id: int, text: str, tags: str, title: str, force: bool, source: str) -> bool:
        if self.db.has_ai_tasks_for_record(record_id) and not force:
            self._skip(
                build_task_extraction_task(record_id, title=title, source=source),
                "Tasks already generated for this record.",
            )
            return False

        resolved_title = (title or "").strip()
        if not resolved_title:
            record = self.db.fetch_record(record_id)
            resolved_title = (
                (record.get("title") or f"Recording {record_id}").strip()
                if isinstance(record, dict)
                else f"Recording {record_id}"
            )
        return self._submit(
            build_task_extraction_task(record_id, text, tags, resolved_title, force, source)
        )

    def enqueue_transcription(self, record_id: int, audio_path: str, model_size: str, language: str | None, diarization: bool, title: str, source: str) -> bool:
        return self._submit(
            build_transcription_task(record_id, audio_path, model_size, language, diarization, title, source)
        )

    def enqueue_rag_reindex(self, scope: str, source: str) -> bool:
        return self._submit(build_rag_reindex_task(scope, source))
