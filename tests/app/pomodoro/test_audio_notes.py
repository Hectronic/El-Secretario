from pathlib import Path

import pytest

from src.app.pomodoro.audio_notes import AudioNoteCapture
from src.database import DBManager


class Recorder:
    is_recording = False

    def __init__(self, path, duration):
        self.path = path
        self.duration = duration

    def start(self):
        self.is_recording = True

    def stop(self):
        self.is_recording = False
        self.path.write_bytes(b"audio-double")
        return str(self.path)

    def get_duration(self, _path):
        return self.duration


def test_empty_audio_capture_cleans_temporary_file_and_reference(tmp_path):
    db = DBManager(str(tmp_path / "audio.sqlite"))
    temporary = tmp_path / "temporary.wav"
    capture = AudioNoteCapture(Recorder(temporary, 0), db, storage_dir=tmp_path / "notes")
    capture.start()
    with pytest.raises(RuntimeError, match="empty"):
        capture.stop_and_save("Voice idea")
    assert not capture.active
    assert not temporary.exists()
    assert db.fetch_timeline() == []
