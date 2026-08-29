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
from types import ModuleType
from unittest.mock import patch

import numpy as np
import pytest

from src.stt_providers import openai_whisper


def test_transcribe_prefers_normalized_model_name_and_serializes_segments(monkeypatch):
    fake_whisper = ModuleType("whisper")
    captured = {}

    class FakeModel:
        def transcribe(self, audio, language=None):
            captured["audio_type"] = type(audio).__name__
            captured["language"] = language
            return {"segments": [{"start": 0, "end": 2, "text": "hola"}]}

    def load_model(model_name):
        captured["model_name"] = model_name
        return FakeModel()

    fake_whisper.load_model = load_model
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    with patch(
        "src.stt_providers.openai_whisper._prepare_audio_for_openai_whisper",
        return_value=np.array([0.0, 1.0], dtype=np.float32),
    ):
        result = openai_whisper.transcribe({"audio_path": "sample.wav", "model_size": "large-v3", "language": "es"})

    assert captured["model_name"] == "large"
    assert captured["language"] == "es"
    assert result == [{"start": 0.0, "end": 2.0, "text": "hola"}]


def test_transcribe_raises_ffmpeg_helpful_error_when_path_mode_missing(monkeypatch):
    fake_whisper = ModuleType("whisper")

    class FakeModel:
        def transcribe(self, audio, language=None):
            raise FileNotFoundError("ffmpeg missing")

    fake_whisper.load_model = lambda model_name: FakeModel()
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    with patch(
        "src.stt_providers.openai_whisper._prepare_audio_for_openai_whisper",
        side_effect=RuntimeError("audio decode failed"),
    ):
        with pytest.raises(RuntimeError, match="FFmpeg is not installed"):
            openai_whisper.transcribe({"audio_path": "sample.wav", "model_size": "base"})
