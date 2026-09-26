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

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.worker_components import subprocess_runner


class _FakeProc:
    def __init__(self, alive_sequence=None, exitcode=0):
        self._alive_sequence = list(alive_sequence or [])
        self.exitcode = exitcode
        self.terminated = False
        self.killed = False
        self.join_calls = []
        self.closed = False
        self.started = False

    def start(self):
        self.started = True

    def is_alive(self):
        if self._alive_sequence:
            return self._alive_sequence.pop(0)
        return False

    def join(self, timeout=None):
        self.join_calls.append(timeout)

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def close(self):
        self.closed = True


class _FakeQueue:
    def __init__(self, result=None, is_empty=False, on_get=None):
        self._result = result or {"ok": True, "segments": [{"start": 0.0, "end": 1.0, "text": "ok"}]}
        self._is_empty = is_empty
        self.closed = False
        self.joined = False
        self.on_get = on_get

    def get(self, timeout=None):
        if self.on_get is not None:
            self.on_get()
        if self._is_empty:
            from queue import Empty
            raise Empty
        return self._result

    def close(self):
        self.closed = True

    def join_thread(self):
        self.joined = True


class _FakeCtx:
    def __init__(self, proc, queue):
        self._proc = proc
        self._queue = queue
        self.process_args = None

    def Queue(self):
        return self._queue

    def Process(self, target=None, args=None, daemon=None):
        self.process_args = {"target": target, "args": args, "daemon": daemon}
        return self._proc


def test_run_backend_subprocess_success():
    proc = _FakeProc(alive_sequence=[True, True, False], exitcode=0)
    queue = _FakeQueue(on_get=lambda: assert_process_is_alive(proc))
    fake_ctx = _FakeCtx(proc, queue)

    with patch("src.worker_components.subprocess_runner.mp.get_context", return_value=fake_ctx), \
         patch("src.worker_components.subprocess_runner.QThread.currentThread", return_value=None):
        segments = subprocess_runner.run_backend_subprocess(
            backend="faster-whisper",
            payload={"audio_path": "x.wav"},
            timeout_seconds=10,
        )

    assert segments[0]["text"] == "ok"
    assert proc.started
    assert queue.closed
    assert queue.joined
    assert proc.closed


def assert_process_is_alive(proc):
    assert proc.is_alive(), "the result must be drained before the child exits"


def test_run_backend_subprocess_waits_for_queue_result_instead_of_using_empty():
    proc = _FakeProc(alive_sequence=[False], exitcode=0)
    queue = _FakeQueue(is_empty=True)
    fake_ctx = _FakeCtx(proc, queue)

    with patch("src.worker_components.subprocess_runner.mp.get_context", return_value=fake_ctx), \
         patch("src.worker_components.subprocess_runner.QThread.currentThread", return_value=None):
        try:
            subprocess_runner.run_backend_subprocess(
                backend="faster-whisper",
                payload={"audio_path": "x.wav"},
                timeout_seconds=10,
            )
        except RuntimeError as exc:
            assert "without returning a result" in str(exc)
        else:
            raise AssertionError("expected missing result error")

    assert queue.closed
    assert proc.closed


def test_run_backend_subprocess_timeout_kills_stubborn_process():
    proc = _FakeProc(alive_sequence=[True, True, False], exitcode=0)
    queue = _FakeQueue()
    fake_ctx = _FakeCtx(proc, queue)

    with patch("src.worker_components.subprocess_runner.mp.get_context", return_value=fake_ctx), \
         patch("src.worker_components.subprocess_runner.time.monotonic", side_effect=[0.0, 10.0]), \
         patch("src.worker_components.subprocess_runner.QThread.currentThread", return_value=None):
        try:
            subprocess_runner.run_backend_subprocess(
                backend="faster-whisper",
                payload={"audio_path": "x.wav"},
                timeout_seconds=5,
            )
        except subprocess_runner.TranscriptionTimeoutError as exc:
            assert "timed out" in str(exc)
        else:
            raise AssertionError("expected timeout")

    assert proc.terminated is True
    assert proc.killed is True
    assert proc.closed is True


def test_run_openai_whisper_fallback_uses_backend_dispatch():
    with patch("src.worker_components.subprocess_runner.run_backend_subprocess", return_value=[{"text": "ok"}]) as mock_run:
        segments = subprocess_runner.run_openai_whisper_fallback(
            audio_path="x.wav",
            model_size="base",
            language="es",
        )

    assert segments == [{"text": "ok"}]
    mock_run.assert_called_once()


def test_faster_whisper_subprocess_uses_speed_profile():
    with patch("src.worker_components.subprocess_runner.run_backend_subprocess", return_value=[]) as mock_run:
        subprocess_runner.run_transcription_in_subprocess(
            audio_path="long.wav",
            model_size="base",
            device="cuda",
            compute_type="float16",
            language="es",
        )

    payload = mock_run.call_args.kwargs["payload"]
    assert payload["beam_size"] == 3
    assert payload["vad_filter"] is True


def test_run_sherpa_onnx_transcription_uses_backend_dispatch():
    with patch("src.worker_components.subprocess_runner.run_backend_subprocess", return_value=[{"text": "ok"}]) as mock_run:
        segments = subprocess_runner.run_sherpa_onnx_transcription(
            audio_path="x.wav",
            language="es",
            model_dir="/tmp/model",
            model_config={"type": "whisper"},
        )

    assert segments == [{"text": "ok"}]
    mock_run.assert_called_once()
