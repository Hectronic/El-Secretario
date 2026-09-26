"""Audio-note capture using the application's existing Recorder contract."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from uuid import uuid4


class AudioNoteCapture:
    def __init__(self, recorder, persistence, *, storage_dir):
        self.recorder = recorder
        self.db = persistence
        self.storage_dir = Path(storage_dir)
        self.active = False

    def start(self):
        if self.active or self.recorder.is_recording:
            raise RuntimeError("Audio capture is already active")
        self.recorder.start()
        self.active = True

    def stop_and_save(self, title, tags=None, pomodoro_id=None):
        if not self.active:
            raise RuntimeError("No audio note is being recorded")
        if not str(title).strip():
            raise ValueError("An audio-note title is required")
        path = None
        destination = None
        try:
            path = self.recorder.stop()
            self.active = False
            if not path or not Path(path).is_file():
                raise RuntimeError("Audio capture did not produce a file")
            duration = float(self.recorder.get_duration(path))
            if duration <= 0:
                raise RuntimeError("Audio note is empty")
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            destination = self.storage_dir / f"note_{uuid4().hex}{Path(path).suffix or '.wav'}"
            shutil.move(path, destination)
            return self.db.create_productivity_note(
                "audio", title, tags or [], audio_ref=str(destination.resolve()),
                duration_seconds=duration, pomodoro_id=pomodoro_id,
            )
        except Exception:
            if self.active:
                try:
                    path = self.recorder.stop()
                except Exception:
                    logging.exception("Failed stopping audio-note capture")
                self.active = False
            if destination and destination.exists():
                destination.unlink()
            elif path and Path(path).exists():
                Path(path).unlink()
            raise

    def cancel(self):
        if not self.active:
            return
        try:
            path = self.recorder.stop()
            if path and Path(path).exists():
                Path(path).unlink()
        finally:
            self.active = False
