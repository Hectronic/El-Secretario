from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer

from src.database import DBManager
from src.ui.recording.media_player_state import PausedState, PlayingState, TrimmingState
from src.ui.recording_widget import RecordingWidget


class FakeMediaPlayer(QObject):
    """Deterministic multimedia edge used while Qt controls remain real."""

    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    playbackStateChanged = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.calls = []
        self.status = QMediaPlayer.MediaStatus.LoadedMedia

    def setAudioOutput(self, output):
        self.audio_output = output

    def setSource(self, source):
        self.source = source

    def play(self):
        self.calls.append("play")
        self.playbackStateChanged.emit(QMediaPlayer.PlaybackState.PlayingState)

    def pause(self):
        self.calls.append("pause")
        self.playbackStateChanged.emit(QMediaPlayer.PlaybackState.PausedState)

    def stop(self):
        self.calls.append("stop")
        self.playbackStateChanged.emit(QMediaPlayer.PlaybackState.StoppedState)

    def setPosition(self, position):
        self.calls.append(("seek", position))
        self.positionChanged.emit(position)

    def mediaStatus(self):
        return self.status


def test_recording_audio_editor_uses_state_context_with_real_qt_controls(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "recording-player.sqlite"))
    record_id = db.save("playback.wav", "", 10.0, "Playback state")
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    (recordings_dir / "playback.wav").write_bytes(b"audio")
    monkeypatch.chdir(tmp_path)
    player = FakeMediaPlayer()

    with patch("src.ui.recording_widget.QMediaPlayer", return_value=player), patch(
        "src.ui.recording_widget.QAudioOutput", return_value=MagicMock()
    ):
        widget = RecordingWidget(
            rag_engine=None,
            record_id=record_id,
            persistence=db,
            audio_edit_mode=True,
        )

    qtbot.addWidget(widget)
    assert widget.play_btn.isEnabled()
    assert not widget.pause_btn.isEnabled()
    assert not widget.stop_btn.isEnabled()

    qtbot.mouseClick(widget.play_btn, Qt.MouseButton.LeftButton)
    assert isinstance(widget.media_player_context.state, PlayingState)
    assert player.calls == ["play"]
    assert widget.pause_btn.isEnabled()
    assert widget.stop_btn.isEnabled()

    qtbot.mouseClick(widget.pause_btn, Qt.MouseButton.LeftButton)
    assert isinstance(widget.media_player_context.state, PausedState)
    assert player.calls == ["play", "pause"]

    widget.media_player_context.trim()
    assert isinstance(widget.media_player_context.state, TrimmingState)
    assert not widget.play_btn.isEnabled()
    assert not widget.pause_btn.isEnabled()
    assert not widget.stop_btn.isEnabled()
    assert not widget.slider.isEnabled()
    assert widget.trim_start_spin.isEnabled()
    assert widget.trim_end_spin.isEnabled()
