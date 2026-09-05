"""Follow-up actions derived from completed summary-queue work."""

from collections.abc import Callable, Iterable
from typing import Any


class QueueCompletionActionCoordinator:
    """Apply completion actions without coupling queue policy to Qt signals."""

    def __init__(
        self,
        db: Any,
        *,
        enqueue_task_extraction: Callable[..., bool],
        enqueue_recording_summary: Callable[..., bool],
        emit_status: Callable[[str], None],
    ):
        self.db = db
        self._enqueue_task_extraction = enqueue_task_extraction
        self._enqueue_recording_summary = enqueue_recording_summary
        self._emit_status = emit_status

    def enqueue_tasks_for_completed_recording(
        self,
        record_id: int,
        title: str,
        *,
        current_task: dict | None,
    ) -> None:
        """Queue AI task extraction after a recording summary when text is available."""
        record = self.db.fetch_record(int(record_id))
        if not isinstance(record, dict):
            return
        ai_text = self.db.get_record_ai_text(int(record_id))
        if not str(ai_text or "").strip():
            return
        source = (current_task or {}).get("source") or "summary"
        self._enqueue_task_extraction(
            int(record_id),
            ai_text,
            record.get("tags") or "",
            title or record.get("title") or f"Recording {record_id}",
            source=source,
        )

    def apply(self, actions: Iterable[dict]) -> None:
        """Dispatch normalized persistence follow-ups to the queue adapter."""
        for action in actions:
            action_type = action.get("type")
            if action_type == "enqueue_task_extraction":
                self._enqueue_task_extraction(
                    action["record_id"],
                    action.get("text", ""),
                    action.get("tags", ""),
                    action.get("title", ""),
                    source=action.get("source") or "summary",
                )
            elif action_type == "enqueue_recording_summary":
                self._enqueue_recording_summary(
                    action["record_id"],
                    action.get("text", ""),
                    action.get("title", ""),
                    source=action.get("source") or "transcription",
                )
            elif action_type == "status":
                self._emit_status(action.get("message", ""))
