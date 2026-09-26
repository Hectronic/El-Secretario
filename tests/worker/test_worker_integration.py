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
    terminals = []
    thread.terminal.connect(terminals.append)
    with qtbot.waitSignal(thread.finished, timeout=3000) as blocker:
        thread.start()

    result = blocker.args[0]
    assert result["text"] == "hola"
    assert result["backend"] == "faster-whisper"
    qtbot.waitUntil(lambda: len(terminals) == 1, timeout=1000)
    assert terminals == [{"status": "succeeded", "operation_id": thread._terminal.operation_id, "user_message": "", "retryable": False, "preserved_work": True}]


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
    terminals = []
    thread.terminal.connect(terminals.append)

    thread.start()
    qtbot.wait(20)
    thread.requestInterruption()
    qtbot.waitUntil(lambda: not thread.isRunning(), timeout=3000)
    # Cross-thread Qt signals can be delivered after QThread reports stopped,
    # notably on macOS runners. Wait for the queued cancellation notification.
    qtbot.waitUntil(lambda: "Cancelled." in statuses, timeout=1000)
    qtbot.waitUntil(lambda: len(terminals) == 1, timeout=1000)

    assert "Cancelled." in statuses
    assert finished_payloads == []
    assert terminals[0]["status"] == "cancelled"
    assert terminals[0]["retryable"] is True


def test_transcriber_thread_timeout_emits_one_retryable_terminal_outcome(qtbot, monkeypatch, tmp_path):
    audio_path = tmp_path / "timeout.wav"
    _write_dummy_audio(audio_path)
    monkeypatch.setattr(
        "src.worker_components.transcriber_thread._run_transcription_in_subprocess",
        lambda **_kwargs: (_ for _ in ()).throw(subprocess_runner.TranscriptionTimeoutError("timed out")),
    )
    thread = TranscriberThread(str(audio_path), device="cpu", compute_type="int8")
    terminals = []
    thread.terminal.connect(terminals.append)

    thread.start()
    qtbot.waitUntil(lambda: len(terminals) == 1, timeout=3000)

    assert terminals[0]["status"] == "timed_out"
    assert terminals[0]["retryable"] is True


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


def test_long_audio_diarization_worker_reports_batched_cuda_progress(qtbot, monkeypatch, tmp_path):
    audio_path = tmp_path / "long-diarization.wav"
    _write_dummy_audio(audio_path)

    class FakeAnnotation:
        @staticmethod
        def itertracks(*, yield_label):
            assert yield_label is True
            return iter([])

    class FakePipeline:
        def __init__(self):
            self.segmentation_batch_size = 1
            self.embedding_batch_size = 1

        def to(self, _device):
            return self

        def __call__(self, _path, *, hook):
            hook("segmentation", None, completed=5, total=10)
            hook("segmentation", object())
            hook("speaker_counting", object())
            hook("embeddings", None, completed=0, total=4)
            hook("embeddings", None, completed=2, total=4)
            hook("embeddings", None, completed=4, total=4)
            hook("embeddings", object())
            hook("discrete_diarization", object())
            return FakeAnnotation()

    pipeline = FakePipeline()

    class FakePipelineClass:
        @staticmethod
        def from_pretrained(_model, *, use_auth_token):
            assert use_auth_token == "hf_test"
            return pipeline

    monkeypatch.setattr(
        "src.worker_components.transcriber_thread._run_transcription_in_subprocess",
        lambda **_kwargs: [{"start": 0.0, "end": 3600.0, "text": "long transcript"}],
    )
    monkeypatch.setattr(
        "src.worker_components.transcriber_thread.worker_settings.get_transcription_chunking_config",
        lambda _settings: {"enabled": False, "threshold_seconds": 1800},
    )
    monkeypatch.setattr(
        "src.worker_components.transcriber_thread._get_pyannote_pipeline_class",
        lambda: FakePipelineClass,
    )
    monkeypatch.setattr(
        "src.worker_components.transcriber_thread._should_use_gpu_for_diarization",
        lambda **_kwargs: (True, "test CUDA device"),
    )
    monkeypatch.setattr(
        "src.worker_components.transcriber_thread.torch.cuda.mem_get_info",
        lambda: (int(6 * 1024**3), int(8 * 1024**3)),
    )
    monkeypatch.setattr("src.worker_components.transcriber_thread.release_local_inference_resources", lambda: None)

    thread = TranscriberThread(
        str(audio_path),
        model_size="base",
        device="cuda",
        compute_type="float16",
        language="es",
        hf_token="hf_test",
        enable_diarization=True,
        total_duration=3600.0,
    )
    progress: list[int] = []
    statuses: list[str] = []
    thread.progress.connect(progress.append)
    thread.status_update.connect(statuses.append)

    with qtbot.waitSignal(thread.finished, timeout=3000) as blocker:
        thread.start()
    qtbot.waitUntil(lambda: not thread.isRunning(), timeout=1000)

    assert blocker.args[0]["text"] == "long transcript"
    assert blocker.args[0]["is_diarized"] is True
    assert pipeline.segmentation_batch_size == 4
    assert pipeline.embedding_batch_size == 4
    assert 82 in progress
    assert 87 in progress
    assert 89 in progress
    assert "Diarizing: segmentation (5/10)" in statuses
    assert "Diarizing: embeddings (2/4)" in statuses
    assert "Diarizing: speaker counting..." in statuses
    assert "Diarizing: speaker clustering..." in statuses
    assert "Diarizing: reconstructing diarization..." in statuses
