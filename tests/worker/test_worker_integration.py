# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import time
from pathlib import Path

import pytest

from src.worker_components.transcriber_thread import TranscriberThread
from src.worker_components import subprocess_runner


def _write_dummy_audio(path: Path) -> None:
    # The worker only needs a readable file size in these tests.
    path.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")


def test_transcriber_thread_async_happy_path_with_real_qthread(qtbot, monkeypatch, tmp_path):
    audio_path = tmp_path / "sample.wav"
    _write_dummy_audio(audio_path)

    monkeypatch.setattr(
        "src.worker_components.transcriber_thread._run_transcription_in_subprocess",
        lambda **_kwargs: [{"start": 0.0, "end": 1.0, "text": "hola"}],
    )
    monkeypatch.setattr("src.worker_components.transcriber_thread._get_pyannote_pipeline_class", lambda: None)

    thread = TranscriberThread(
        str(audio_path),
        model_size="base",
        device="cpu",
        compute_type="int8",
        total_duration=1.0,
    )
    with qtbot.waitSignal(thread.finished, timeout=3000) as blocker:
        thread.start()

    result = blocker.args[0]
    assert result["text"] == "hola"
    assert result["backend"] == "faster-whisper"


def test_transcriber_thread_interrupts_cleanly_without_finished(qtbot, monkeypatch, tmp_path):
    audio_path = tmp_path / "interrupt.wav"
    _write_dummy_audio(audio_path)

    def _slow_transcribe(**_kwargs):
        time.sleep(0.08)
        return [{"start": 0.0, "end": 30.0, "text": "long segment"}]

    monkeypatch.setattr("src.worker_components.transcriber_thread._run_transcription_in_subprocess", _slow_transcribe)
    monkeypatch.setattr("src.worker_components.transcriber_thread._get_pyannote_pipeline_class", lambda: None)

    thread = TranscriberThread(
        str(audio_path),
        model_size="base",
        device="cpu",
        compute_type="int8",
        total_duration=30.0,
    )
    statuses: list[str] = []
    finished_payloads: list[dict] = []
    thread.status_update.connect(statuses.append)
    thread.finished.connect(finished_payloads.append)

    thread.start()
    qtbot.wait(20)
    thread.requestInterruption()
    qtbot.waitUntil(lambda: not thread.isRunning(), timeout=3000)
    # Cross-thread Qt signals can be delivered after QThread reports stopped,
    # notably on macOS runners. Wait for the queued cancellation notification.
    qtbot.waitUntil(lambda: "Cancelled." in statuses, timeout=1000)

    assert "Cancelled." in statuses
    assert finished_payloads == []


def test_subprocess_runner_real_process_reports_unsupported_backend():
    # This test exercises real spawn + IPC with dispatcher error propagation.
    with pytest.raises(RuntimeError) as exc:
        subprocess_runner.run_backend_subprocess(
            backend="missing-backend",
            payload={"audio_path": "x.wav"},
            timeout_seconds=10,
        )
    assert "Unsupported transcription backend" in str(exc.value)


def test_transcriber_thread_repeated_runs_do_not_hang(qtbot, monkeypatch, tmp_path):
    audio_path = tmp_path / "loop.wav"
    _write_dummy_audio(audio_path)

    monkeypatch.setattr(
        "src.worker_components.transcriber_thread._run_transcription_in_subprocess",
        lambda **_kwargs: [{"start": 0.0, "end": 0.2, "text": "ok"}],
    )
    monkeypatch.setattr("src.worker_components.transcriber_thread._get_pyannote_pipeline_class", lambda: None)

    for _ in range(12):
        thread = TranscriberThread(
            str(audio_path),
            model_size="base",
            device="cpu",
            compute_type="int8",
            total_duration=0.2,
        )
        with qtbot.waitSignal(thread.finished, timeout=3000):
            thread.start()
        qtbot.waitUntil(lambda: not thread.isRunning(), timeout=1000)
