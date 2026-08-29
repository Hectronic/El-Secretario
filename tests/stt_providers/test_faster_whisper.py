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
from types import SimpleNamespace, ModuleType
from unittest.mock import patch

from src.stt_providers import faster_whisper


def test_transcribe_serializes_faster_whisper_segments(monkeypatch):
    fake_module = ModuleType("faster_whisper")
    captured = {}

    class FakeModel:
        def __init__(self, model_size, device, compute_type, cpu_threads):
            captured["init"] = (model_size, device, compute_type, cpu_threads)

        def transcribe(self, audio_path, beam_size=5, language=None):
            captured["transcribe"] = (audio_path, beam_size, language)
            return [SimpleNamespace(start=0, end=1.5, text="hola")], None

    fake_module.WhisperModel = FakeModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)

    with patch("src.stt_providers.faster_whisper.platform.system", return_value="Linux"):
        result = faster_whisper.transcribe(
            {
                "audio_path": "sample.wav",
                "model_size": "base",
                "device": "cpu",
                "compute_type": "int8",
                "language": "es",
            }
        )

    assert captured["init"] == ("base", "cpu", "int8", 4)
    assert captured["transcribe"] == ("sample.wav", 5, "es")
    assert result == [{"start": 0.0, "end": 1.5, "text": "hola"}]
