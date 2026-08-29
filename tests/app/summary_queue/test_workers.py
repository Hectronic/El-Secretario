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

from src.app.summary_queue.workers import build_transcription_worker_kwargs


class _FakeSettings:
    def __init__(self, values):
        self.values = values

    def value(self, key, default=None, type=None):  # noqa: A002
        return self.values.get(key, default)


def test_build_transcription_worker_kwargs_normalizes_auto_compute_and_keeps_runtime_flags(monkeypatch):
    monkeypatch.setattr(
        "src.app.summary_queue.workers.read_audio_duration_seconds",
        lambda _path: 12.5,
    )
    settings = _FakeSettings(
        {
            "hf_token": "hf_x",
            "force_cpu": True,
            "compute_type": "auto",
            "transcription_backend": "faster-whisper",
        }
    )

    kwargs = build_transcription_worker_kwargs(
        settings,
        {
            "audio_path": "/tmp/audio.wav",
            "model_size": "large-v3",
            "language": "es",
            "diarization": True,
        },
    )

    assert kwargs == {
        "audio_path": "/tmp/audio.wav",
        "model_size": "large-v3",
        "compute_type": None,
        "language": "es",
        "hf_token": "hf_x",
        "enable_diarization": True,
        "total_duration": 12.5,
        "force_cpu": True,
        "backend_preference": "faster-whisper",
    }
