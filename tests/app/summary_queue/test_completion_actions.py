from unittest.mock import Mock

from src.app.summary_queue.completion_actions import QueueCompletionActionCoordinator


def _coordinator(db):
    enqueue_tasks = Mock(return_value=True)
    enqueue_summary = Mock(return_value=True)
    emit_status = Mock()
    return (
        QueueCompletionActionCoordinator(
            db,
            enqueue_task_extraction=enqueue_tasks,
            enqueue_recording_summary=enqueue_summary,
            emit_status=emit_status,
        ),
        enqueue_tasks,
        enqueue_summary,
        emit_status,
    )


def test_completed_recording_queues_task_extraction_with_current_task_source():
    db = Mock()
    db.fetch_record.return_value = {"title": "Stored title", "tags": "work"}
    db.get_record_ai_text.return_value = "Summary text"
    coordinator, enqueue_tasks, _, _ = _coordinator(db)

    coordinator.enqueue_tasks_for_completed_recording(
        12,
        "",
        current_task={"source": "daily_summary"},
    )

    enqueue_tasks.assert_called_once_with(
        12, "Summary text", "work", "Stored title", source="daily_summary"
    )


def test_completed_recording_skips_follow_up_without_persisted_ai_text():
    db = Mock()
    db.fetch_record.return_value = {"title": "Stored title", "tags": "work"}
    db.get_record_ai_text.return_value = ""
    coordinator, enqueue_tasks, _, _ = _coordinator(db)

    coordinator.enqueue_tasks_for_completed_recording(12, "Title", current_task=None)

    enqueue_tasks.assert_not_called()


def test_apply_dispatches_known_completion_actions():
    coordinator, enqueue_tasks, enqueue_summary, emit_status = _coordinator(Mock())

    coordinator.apply(
        [
            {"type": "enqueue_task_extraction", "record_id": 1, "text": "tasks", "tags": "a"},
            {"type": "enqueue_recording_summary", "record_id": 2, "text": "note", "title": "Title"},
            {"type": "status", "message": "Done"},
            {"type": "unknown"},
        ]
    )

    enqueue_tasks.assert_called_once_with(1, "tasks", "a", "", source="summary")
    enqueue_summary.assert_called_once_with(2, "note", "Title", source="transcription")
    emit_status.assert_called_once_with("Done")
