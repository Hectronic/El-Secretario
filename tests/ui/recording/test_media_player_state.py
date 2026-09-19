from unittest.mock import MagicMock

from PyQt6.QtMultimedia import QMediaPlayer

from src.ui.recording.media_player_state import (
    MediaPlayerContext,
    PausedState,
    PlayingState,
    StoppedState,
    TrimmingState,
)


def _context(*, audio_editor=True):
    widget = MagicMock()
    widget.player = MagicMock()
    widget.play_btn = MagicMock()
    widget.pause_btn = MagicMock()
    widget.stop_btn = MagicMock()
    widget.slider = MagicMock()
    widget.audio_edit_group = MagicMock() if audio_editor else None
    return MediaPlayerContext(widget), widget


def test_stopped_state_enables_play_and_blocks_invalid_pause_and_stop():
    context, widget = _context()

    context.set_source_available(True)
    context.pause()
    context.stop()

    assert isinstance(context.state, StoppedState)
    widget.player.pause.assert_not_called()
    widget.player.stop.assert_not_called()
    widget.play_btn.setEnabled.assert_called_with(True)
    widget.pause_btn.setEnabled.assert_called_with(False)
    widget.stop_btn.setEnabled.assert_called_with(False)


def test_play_pause_and_stop_follow_state_transitions():
    context, widget = _context()
    context.set_source_available(True)

    context.play()
    assert isinstance(context.state, PlayingState)
    widget.player.play.assert_called_once_with()
    widget.play_btn.setEnabled.assert_called_with(False)
    widget.pause_btn.setEnabled.assert_called_with(True)

    context.pause()
    assert isinstance(context.state, PausedState)
    widget.player.pause.assert_called_once_with()
    widget.play_btn.setEnabled.assert_called_with(True)
    widget.stop_btn.setEnabled.assert_called_with(True)

    context.stop()
    assert isinstance(context.state, StoppedState)
    widget.player.stop.assert_called_once_with()


def test_trim_from_active_playback_pauses_and_locks_playback_controls():
    context, widget = _context()
    context.set_source_available(True)
    context.play()

    context.trim()

    assert isinstance(context.state, TrimmingState)
    widget.player.pause.assert_called_once_with()
    widget.play_btn.setEnabled.assert_called_with(False)
    widget.pause_btn.setEnabled.assert_called_with(False)
    widget.stop_btn.setEnabled.assert_called_with(False)
    widget.slider.setEnabled.assert_called_with(False)
    widget._set_audio_edit_enabled.assert_called_with(True)

    context.play()
    context.pause()
    context.stop()
    context.seek(250)
    widget.player.play.assert_called_once_with()
    widget.player.pause.assert_called_once_with()
    widget.player.stop.assert_not_called()
    widget.player.setPosition.assert_not_called()


def test_finish_trim_stops_backend_and_restores_stopped_controls():
    context, widget = _context()
    context.set_source_available(True)
    context.trim()

    context.finish_trim()

    assert isinstance(context.state, StoppedState)
    widget.player.stop.assert_called_once_with()
    widget.play_btn.setEnabled.assert_called_with(True)
    widget.pause_btn.setEnabled.assert_called_with(False)
    widget.stop_btn.setEnabled.assert_called_with(False)


def test_end_of_media_transitions_playing_state_to_stopped():
    context, widget = _context()
    widget.player.mediaStatus.return_value = QMediaPlayer.MediaStatus.EndOfMedia
    context.set_source_available(True)
    context.play()

    context.media_state_changed(QMediaPlayer.PlaybackState.StoppedState)

    assert isinstance(context.state, StoppedState)
    widget.player.stop.assert_called_once_with()


def test_context_ignores_actions_without_an_audio_source():
    context, widget = _context()

    context.play()
    context.pause()
    context.stop()
    context.seek(10)
    context.trim()

    assert isinstance(context.state, StoppedState)
    widget.player.play.assert_not_called()
    widget.player.pause.assert_not_called()
    widget.player.stop.assert_not_called()
    widget.player.setPosition.assert_not_called()
