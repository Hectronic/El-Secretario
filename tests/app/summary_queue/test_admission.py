from unittest.mock import Mock

from src.app.summary_queue.admission import QueueTaskAdmissionCoordinator


def _coordinator(db):
    submit, skip = Mock(return_value=True), Mock()
    return QueueTaskAdmissionCoordinator(db, submit=submit, skip=skip), submit, skip


def test_task_extraction_resolves_record_title_before_submission():
    db = Mock()
    db.has_ai_tasks_for_record.return_value = False
    db.fetch_record.return_value = {"title": "Saved title"}
    coordinator, submit, _ = _coordinator(db)

    assert coordinator.enqueue_task_extraction(3, "text", "tags", "", False, "summary") is True

    assert submit.call_args.args[0]["title"] == "Saved title"


def test_task_extraction_with_existing_ai_tasks_is_skipped():
    db = Mock()
    db.has_ai_tasks_for_record.return_value = True
    coordinator, submit, skip = _coordinator(db)

    assert coordinator.enqueue_task_extraction(3, "text", "tags", "Title", False, "manual") is False

    submit.assert_not_called()
    assert skip.call_args.args[1] == "Tasks already generated for this record."


def test_daily_summary_without_date_is_skipped():
    coordinator, submit, skip = _coordinator(Mock())

    assert coordinator.enqueue_daily_summary({}) is False

    submit.assert_not_called()
    assert skip.call_args.args == ({}, "Daily summary task missing date.")
