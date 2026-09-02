from unittest.mock import MagicMock, patch

from src.ui.recording.record_details import RecordingDetailsCoordinator


def test_save_all_changes_persists_detail_indexes_and_marks_widget_clean():
    widget = MagicMock()
    widget.current_record_id = 9
    widget.title_input.text.return_value = " Planning "
    widget.text_display.toPlainText.return_value = "Transcript"
    widget.notes_display.toPlainText.return_value = " Notes "
    widget.tags_input.text.return_value = "work"
    widget.is_diarized_check_meta.isChecked.return_value = True
    widget.date_label.text.return_value = "2026-09-01"

    with patch("src.ui.recording.record_details.index_saved_record_changes") as index_changes:
        saved = RecordingDetailsCoordinator(widget).save_all_changes()

    assert saved is True
    widget.db.update_title.assert_called_once_with(9, "Planning")
    widget.db.update_transcription.assert_called_once_with(9, "Transcript", is_diarized=True)
    widget.db.update_recording_notes.assert_called_once_with(9, "Notes")
    widget.db.update_tags.assert_called_once_with(9, "work")
    index_changes.assert_called_once()
    assert index_changes.call_args.kwargs["record_id"] == 9
    assert index_changes.call_args.kwargs["tags"] == "work"
    widget._set_dirty.assert_called_once_with(False)
    widget.recording_saved.emit.assert_called_once_with()
    widget.status_changed.emit.assert_called_once_with("Saved.")


def test_save_all_changes_returns_false_without_a_record():
    widget = MagicMock()
    widget.current_record_id = None

    assert RecordingDetailsCoordinator(widget).save_all_changes() is False
    widget.db.update_title.assert_not_called()


def test_load_record_ignores_missing_rows():
    widget = MagicMock()
    widget.db.fetch_record.return_value = None

    RecordingDetailsCoordinator(widget).load_record(55)

    widget._set_dirty.assert_not_called()
