from unittest.mock import MagicMock, patch

from src.ui.recording.transcription_actions import RecordingTranscriptionCoordinator


def _result():
    return {
        "text": "Transcript",
        "model_name": "base",
        "audio_duration": 5.0,
        "audio_size_bytes": 100,
        "transcription_time": 0.2,
        "is_diarized": False,
    }


def test_finished_transcription_persists_refreshes_and_indexes_result():
    widget = MagicMock()
    widget.current_record_id = 4
    widget.current_recording_path = "/tmp/call.wav"
    widget.auto_summarize_after_transcription = False
    widget.date_label.text.return_value = "2026-09-01"
    coordinator = RecordingTranscriptionCoordinator(widget)

    with patch(
        "src.ui.recording.transcription_actions.persist_direct_transcription_result",
        return_value=4,
    ) as persist, patch(
        "src.ui.recording.transcription_actions.index_transcription_result_after_refresh"
    ) as index_result:
        coordinator.on_transcription_finished(_result(), settings_cls=MagicMock)

    persist.assert_called_once_with(widget.db, 4, "call.wav", _result())
    widget.text_display.setText.assert_called_once_with("Transcript")
    widget.load_record.assert_called_once_with(4)
    widget.recording_saved.emit.assert_called_once_with()
    index_result.assert_called_once()
    assert index_result.call_args.kwargs["title"] == "call.wav"


def test_transcription_error_and_status_preserve_widget_signals_and_traces():
    widget = MagicMock()
    widget.current_record_id = 4
    message_box = MagicMock()
    coordinator = RecordingTranscriptionCoordinator(widget)

    coordinator.on_transcription_error("broken", message_box=message_box)
    coordinator.on_status_update("Loading")

    widget.status_changed.emit.assert_any_call("Failed.")
    widget.status_changed.emit.assert_any_call("Loading")
    widget.progress_changed.emit.assert_called_once_with(-2)
    widget.retranscribe_btn.setEnabled.assert_called_once_with(True)
    message_box.critical.assert_called_once_with(widget, "Error", "broken")
    assert widget.summary_task_queue.add_external_trace.call_count == 2


def test_set_transcription_config_updates_controls_and_auto_summary():
    widget = MagicMock()
    widget.model_combo.findText.return_value = 2
    widget.lang_combo.findText.return_value = 1

    RecordingTranscriptionCoordinator(widget).set_transcription_config(
        {
            "model": "large-v3",
            "language": "es",
            "diarization": True,
            "auto_summarize_after_transcription": "true",
        }
    )

    widget.model_combo.setCurrentIndex.assert_called_once_with(2)
    widget.lang_combo.setCurrentIndex.assert_called_once_with(1)
    widget.diarization_check.setChecked.assert_called_once_with(True)
    assert widget.auto_summarize_after_transcription is True
