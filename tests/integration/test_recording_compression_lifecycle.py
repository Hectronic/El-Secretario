from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import soundfile as sf
from PyQt6.QtWidgets import QTabWidget, QWidget

from src.database import DBManager
from src.ui.main_window.recording_tabs import RecordingTabCoordinator


def test_completed_capture_compresses_after_transcription_source_is_released(qtbot, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    source = recordings_dir / "capture.wav"
    sf.write(source, np.zeros(16000 * 2, dtype=np.float32), 16000)

    window = MagicMock()
    window.central_tabs = QTabWidget()
    window.db = DBManager(str(tmp_path / "capture.sqlite"))
    window.rag = None
    window.recorder = MagicMock()
    window.summary_task_queue = None
    coordinator = RecordingTabCoordinator(window)

    def encoder(path):
        target = Path(path).with_suffix(".mp3")
        target.write_bytes(b"compressed")
        return str(target)

    with patch(
        "src.ui.recording_widget.RecordingWidget.start_transcription_with_config",
        return_value=None,
    ), patch("src.audio.compress_wav_to_mp3", side_effect=encoder):
        coordinator.on_recording_finished(
            str(source), {"title": "Compressed capture"}, QWidget()
        )

    widget = window.central_tabs.currentWidget()
    target = recordings_dir / "capture.mp3"
    qtbot.waitUntil(
        lambda: window.db.fetch_all()[0]["filename"] == "capture.mp3"
        and widget.current_recording_path == str(target),
        timeout=5000,
    )

    assert target.exists()
    assert not source.exists()
    assert widget.db is window.db
