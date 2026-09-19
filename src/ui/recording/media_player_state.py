"""State-driven controls for the recording detail media player."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from PyQt6.QtMultimedia import QMediaPlayer

if TYPE_CHECKING:
    from src.ui.recording_widget import RecordingWidget


class PlayerState(ABC):
    """Behaviour and control availability for one playback state."""

    play_enabled = False
    pause_enabled = False
    stop_enabled = False
    seek_enabled = False
    trim_enabled = False

    def play(self, context: "MediaPlayerContext") -> None:
        """Ignore play when it is not valid for this state."""

    def pause(self, context: "MediaPlayerContext") -> None:
        """Ignore pause when it is not valid for this state."""

    def stop(self, context: "MediaPlayerContext") -> None:
        """Ignore stop when it is not valid for this state."""

    def seek(self, context: "MediaPlayerContext", position: int) -> None:
        """Ignore seeks when the player is locked."""

    def trim(self, context: "MediaPlayerContext") -> None:
        """Ignore trimming when it is not valid for this state."""

    def finish_trim(self, context: "MediaPlayerContext") -> None:
        """Return to stopped playback when a trim operation finishes."""
        context.transition_to(StoppedState())


class StoppedState(PlayerState):
    play_enabled = True
    seek_enabled = True
    trim_enabled = True

    def play(self, context: "MediaPlayerContext") -> None:
        context.player.play()
        context.transition_to(PlayingState())

    def seek(self, context: "MediaPlayerContext", position: int) -> None:
        context.player.setPosition(position)

    def trim(self, context: "MediaPlayerContext") -> None:
        context.transition_to(TrimmingState())


class PlayingState(PlayerState):
    pause_enabled = True
    stop_enabled = True
    seek_enabled = True
    trim_enabled = True

    def pause(self, context: "MediaPlayerContext") -> None:
        context.player.pause()
        context.transition_to(PausedState())

    def stop(self, context: "MediaPlayerContext") -> None:
        context.player.stop()
        context.transition_to(StoppedState())

    def seek(self, context: "MediaPlayerContext", position: int) -> None:
        context.player.setPosition(position)

    def trim(self, context: "MediaPlayerContext") -> None:
        context.player.pause()
        context.transition_to(TrimmingState())


class PausedState(PlayerState):
    play_enabled = True
    stop_enabled = True
    seek_enabled = True
    trim_enabled = True

    def play(self, context: "MediaPlayerContext") -> None:
        context.player.play()
        context.transition_to(PlayingState())

    def stop(self, context: "MediaPlayerContext") -> None:
        context.player.stop()
        context.transition_to(StoppedState())

    def seek(self, context: "MediaPlayerContext", position: int) -> None:
        context.player.setPosition(position)

    def trim(self, context: "MediaPlayerContext") -> None:
        context.transition_to(TrimmingState())


class TrimmingState(PlayerState):
    """Locks playback controls while trim inputs remain available."""

    trim_enabled = True

    def finish_trim(self, context: "MediaPlayerContext") -> None:
        context.player.stop()
        context.transition_to(StoppedState())


class MediaPlayerContext:
    """Own playback state and synchronize the recording widget controls."""

    def __init__(self, widget: "RecordingWidget"):
        self.widget = widget
        self.state: PlayerState = StoppedState()
        self.source_available = False

    @property
    def player(self):
        return self.widget.player

    def transition_to(self, state: PlayerState) -> None:
        self.state = state
        self.sync_ui()

    def set_source_available(self, available: bool) -> None:
        self.source_available = bool(available)
        if not self.source_available:
            self.state = StoppedState()
        self.sync_ui()

    def play(self) -> None:
        if self.source_available:
            self.state.play(self)

    def pause(self) -> None:
        if self.source_available:
            self.state.pause(self)

    def stop(self) -> None:
        if self.source_available:
            self.state.stop(self)

    def seek(self, position: int) -> None:
        if self.source_available:
            self.state.seek(self, position)

    def trim(self) -> None:
        if self.source_available and getattr(self.widget, "audio_edit_group", None):
            self.state.trim(self)

    def finish_trim(self) -> None:
        """Return safely to stopped playback after a trim operation."""
        self.state.finish_trim(self)

    def media_state_changed(self, _state: QMediaPlayer.PlaybackState) -> None:
        """Handle asynchronous backend completion without dereferencing stale state."""
        if self.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            if isinstance(self.state, PlayingState):
                self.state.stop(self)
            else:
                self.transition_to(StoppedState())

    def sync_ui(self) -> None:
        """Apply the active state to controls that have already been constructed."""
        available = self.source_available
        self._set_enabled("play_btn", available and self.state.play_enabled)
        self._set_enabled("pause_btn", available and self.state.pause_enabled)
        self._set_enabled("stop_btn", available and self.state.stop_enabled)
        self._set_enabled("slider", available and self.state.seek_enabled)

        if getattr(self.widget, "audio_edit_group", None):
            self.widget._set_audio_edit_enabled(available and self.state.trim_enabled)

    def _set_enabled(self, attribute: str, enabled: bool) -> None:
        control = getattr(self.widget, attribute, None)
        if control is not None:
            control.setEnabled(enabled)
