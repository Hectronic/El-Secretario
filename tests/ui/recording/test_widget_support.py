from unittest.mock import MagicMock

from src.ui.recording.widget_support import RecordingWidgetSupport


def test_dirty_state_updates_save_button_and_respects_suppression():
    widget = MagicMock()
    widget._suppress_dirty_tracking = False
    support = RecordingWidgetSupport(widget)

    support.mark_dirty()

    assert widget._has_unsaved_changes is True
    widget.save_all_btn.setEnabled.assert_called_once_with(True)
    widget.reset_mock()
    widget._suppress_dirty_tracking = True
    support.mark_dirty()
    widget.save_all_btn.setEnabled.assert_not_called()


def test_cleanup_stops_player_and_releases_threads():
    widget = MagicMock()
    thread = MagicMock()
    thread.isRunning.return_value = True
    widget.transcriber_thread = thread
    widget.ai_thread = None

    RecordingWidgetSupport(widget).cleanup(qurl=MagicMock())

    widget.stop_audio.assert_called_once_with()
    thread.requestInterruption.assert_called_once_with()
    thread.quit.assert_called_once_with()
    thread.wait.assert_called_once_with(3000)
    thread.deleteLater.assert_called_once_with()
    assert widget.transcriber_thread is None
