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

import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from src.stt_providers import sherpa_onnx


def test_create_sherpa_onnx_recognizer_supports_whisper_mode():
    fake_module = ModuleType("sherpa_onnx")
    captured = {}

    class OfflineRecognizer:
        @staticmethod
        def from_whisper(**kwargs):
            captured.update(kwargs)
            return "recognizer"

    fake_module.OfflineRecognizer = OfflineRecognizer

    recognizer = sherpa_onnx.create_sherpa_onnx_recognizer(
        sherpa_onnx_module=fake_module,
        model_config={"type": "whisper", "encoder": "enc", "decoder": "dec", "tokens": "tok"},
        language="es",
    )

    assert recognizer == "recognizer"
    assert captured["language"] == "es"
    assert captured["tokens"] == "tok"


def test_transcribe_serializes_sherpa_result(monkeypatch):
    fake_soundfile = ModuleType("soundfile")
    fake_soundfile.read = lambda path, always_2d=False: (np.array([0.0, 1.0, 2.0], dtype=np.float32), 16000)
    monkeypatch.setitem(sys.modules, "soundfile", fake_soundfile)

    fake_sherpa = ModuleType("sherpa_onnx")
    captured = {}

    class FakeStream:
        def __init__(self):
            self.result = SimpleNamespace(text="hola mundo")

        def accept_waveform(self, sample_rate, audio):
            captured["sample_rate"] = sample_rate
            captured["audio_len"] = len(audio)

    class OfflineRecognizer:
        @staticmethod
        def from_whisper(**kwargs):
            captured["config"] = kwargs
            return OfflineRecognizer()

        def create_stream(self):
            return FakeStream()

        def decode_streams(self, streams):
            captured["decode_streams"] = len(streams)

    fake_sherpa.OfflineRecognizer = OfflineRecognizer
    monkeypatch.setitem(sys.modules, "sherpa_onnx", fake_sherpa)

    result = sherpa_onnx.transcribe(
        {
            "audio_path": "sample.wav",
            "language": "es",
            "model_config": {"type": "whisper", "encoder": "enc", "decoder": "dec", "tokens": "tok"},
        }
    )

    assert captured["sample_rate"] == 16000
    assert captured["decode_streams"] == 1
    assert result == [{"start": 0.0, "end": pytest.approx(3 / 16000), "text": "hola mundo"}]
