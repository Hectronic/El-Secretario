import numpy as np
import soundfile as sf

from src.database import DBManager
from src.ui.audio_editor.editing_state import AudioChunk
from src.ui.audio_editor.transcription_runtime import AudioEditorTranscriptionRuntime
from src.ui.audio_editor.widget import AudioEditorWidget


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, value):
        for callback in list(self.callbacks):
            callback(value)


class _ImmediateTranscriber:
    def __init__(self, *_args, **_kwargs):
        self.finished = _Signal()
        self.error = _Signal()
        self.running = False

    def isRunning(self):
        return self.running

    def start(self):
        self.running = True
        self.finished.emit({
            "text": "Updated transcription",
            "is_diarized": False,
            "model_name": "test-model",
            "audio_duration": 0.5,
            "audio_size_bytes": 12,
            "transcription_time": 0.01,
        })
        self.running = False

    def requestInterruption(self):
        self.running = False

    def quit(self):
        pass

    def wait(self, _timeout):
        return True

    def deleteLater(self):
        pass


class _MediaSignal:
    def connect(self, _callback):
        pass


class _MediaPlayer:
    def __init__(self):
        self.positionChanged = _MediaSignal()
        self.durationChanged = _MediaSignal()
        self.playbackStateChanged = _MediaSignal()

    def setAudioOutput(self, _output):
        pass

    def setSource(self, _source):
        pass

    def position(self):
        return 0

    def stop(self):
        pass


class _AudioOutput:
    def setVolume(self, _volume):
        pass


class _Settings:
    def value(self, _key, default=None, **_kwargs):
        return default


def test_audio_editor_apply_persists_backup_duration_and_transcription(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "audio-editor.sqlite"))
    recordings = tmp_path / "recordings"
    recordings.mkdir()
    path = recordings / "edited.wav"
    audio = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
    sf.write(path, audio, 4)
    record_id = db.save("edited.wav", "Original transcription", 1.0, "Edited")
    runtime = AudioEditorTranscriptionRuntime(
        thread_factory=_ImmediateTranscriber,
        settings_factory=lambda *_args: _Settings(),
        model_resolver=lambda _settings: "base",
        preflight_checker=lambda *_args: None,
    )
    monkeypatch.setattr("src.ui.audio_editor.widget.QMediaPlayer", _MediaPlayer)
    monkeypatch.setattr("src.ui.audio_editor.widget.QAudioOutput", _AudioOutput)
    monkeypatch.setattr("src.ui.audio_editor.widget.QMessageBox.critical", lambda *_args: None)
    widget = AudioEditorWidget(
        rag_engine=None,
        record_id=None,
        persistence=db,
        transcription_runtime=runtime,
    )
    qtbot.addWidget(widget)
    widget.current_record_id = record_id
    widget.current_recording_path = str(path)
    widget.current_audio = audio.reshape(-1, 1)
    widget.preview_audio = audio[:2].reshape(-1, 1)
    widget.current_sample_rate = 4
    widget.current_duration = 1.0
    widget.chunks = [AudioChunk(0.0, 0.5)]
    widget.active_chunk_index = 0
    saved = []
    widget.recording_saved.connect(lambda: saved.append(True))

    assert widget.apply_edits() is True

    record = db.fetch_record(record_id)
    assert (tmp_path / "recordings" / "edited.wav.orig").exists()
    assert sf.info(path).frames == 2
    assert record["duration"] == 0.5
    assert record["transcription"] == "Updated transcription"
    assert saved == [True, True]
    assert runtime.thread is None
