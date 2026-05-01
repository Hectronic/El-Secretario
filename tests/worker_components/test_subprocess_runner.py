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

    def close(self):
        self.closed = True


class _FakeQueue:
    def __init__(self, result=None, is_empty=False):
        self._result = result or {"ok": True, "segments": [{"start": 0.0, "end": 1.0, "text": "ok"}]}
        self._is_empty = is_empty
        self.closed = False
        self.joined = False

    def empty(self):
        return self._is_empty

    def get(self):
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
    proc = _FakeProc(alive_sequence=[True, False], exitcode=0)
    queue = _FakeQueue()
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


def test_run_openai_whisper_fallback_uses_backend_dispatch():
    with patch("src.worker_components.subprocess_runner.run_backend_subprocess", return_value=[{"text": "ok"}]) as mock_run:
        segments = subprocess_runner.run_openai_whisper_fallback(
            audio_path="x.wav",
            model_size="base",
            language="es",
        )

    assert segments == [{"text": "ok"}]
    mock_run.assert_called_once()


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
