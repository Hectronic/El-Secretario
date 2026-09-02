from unittest.mock import MagicMock

from src.ui.recording.ai_orchestration import RecordingAiCoordinator


def _widget():
    widget = MagicMock()
    widget.current_record_id = 8
    widget.title_input.text.return_value = "Planning"
    widget.tags_input.text.return_value = "work"
    widget.text_display.toPlainText.return_value = "Transcript"
    widget.notes_display.toPlainText.return_value = ""
    widget.db.compose_ai_text.return_value = "Transcript"
    return widget


def test_summary_request_uses_central_queue():
    widget = _widget()
    coordinator = RecordingAiCoordinator(widget)

    coordinator.run_ai_task(
        "summary",
        settings_cls=MagicMock,
        assistant_cls=MagicMock,
        validate_provider=MagicMock(),
        message_box=MagicMock(),
    )

    widget.summary_task_queue.enqueue_recording_summary.assert_called_once_with(
        8, "Transcript", "Planning", source="recording"
    )


def test_task_reextract_refreshes_widget_when_existing_tasks_are_replaced():
    widget = _widget()
    widget.db.has_ai_tasks_for_record.return_value = True
    coordinator = RecordingAiCoordinator(widget)

    coordinator.run_ai_task(
        "task_extraction",
        settings_cls=MagicMock,
        assistant_cls=MagicMock,
        validate_provider=MagicMock(),
        message_box=MagicMock(),
    )

    widget.db.delete_ai_tasks_by_record.assert_called_once_with(8)
    widget.tasks_widget.refresh.assert_called_once_with()
    widget.extract_tasks_btn.setText.assert_called_once_with("Re-extract Tasks (AI)")


def test_background_queue_refresh_updates_summary_tasks_and_button():
    widget = _widget()
    widget.db.fetch_record.return_value = {"summary": "Done"}
    widget.db.has_ai_tasks_for_record.return_value = False

    RecordingAiCoordinator(widget).refresh_from_background_queue(
        include_summary=True, include_tasks=True
    )

    widget.summary_display.setText.assert_called_once_with("Done")
    widget.tasks_widget.refresh.assert_called_once_with()
    widget.extract_tasks_btn.setText.assert_called_once_with("Extract Tasks (AI)")
