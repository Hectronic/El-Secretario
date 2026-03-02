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

import importlib
import sys
import types
from unittest.mock import MagicMock

import numpy as np


def _load_audio_module_with_mocks(monkeypatch):
    fake_stream = MagicMock()

    fake_sd = types.SimpleNamespace(
        InputStream=MagicMock(return_value=fake_stream),
        query_devices=MagicMock(return_value=[]),
    )
    fake_sf = types.SimpleNamespace(
        write=MagicMock(),
        SoundFile=MagicMock(),
    )

    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
    monkeypatch.setitem(sys.modules, "soundfile", fake_sf)
    monkeypatch.delitem(sys.modules, "src.audio", raising=False)

    audio_module = importlib.import_module("src.audio")
    return audio_module, fake_sd, fake_sf, fake_stream


def test_start_stop(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    audio_module, fake_sd, fake_sf, fake_stream = _load_audio_module_with_mocks(monkeypatch)

    recorder = audio_module.Recorder()
    recorder.start()

    assert recorder.is_recording is True
    assert recorder.stream is fake_stream
    fake_sd.InputStream.assert_called_once()
    fake_stream.start.assert_called_once()

    recorder.recording = [np.zeros((100, 1), dtype=np.float32)]
    path = recorder.stop()

    assert recorder.is_recording is False
    assert path is not None
    assert path.endswith(".wav")
    fake_sf.write.assert_called_once()
    fake_stream.stop.assert_called_once()
    fake_stream.close.assert_called_once()


def test_pause_resume(monkeypatch):
    audio_module, _, _, _ = _load_audio_module_with_mocks(monkeypatch)

    recorder = audio_module.Recorder()
    recorder.start()
    recorder.pause()
    assert recorder.is_paused is True

    recorder.resume()
    assert recorder.is_paused is False
