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

import numpy as np
from PyQt6 import sip
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.ui.audio_editor.waveform import AudioWaveformWidget


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication(sys.argv)
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


def test_waveform_tracks_audio_duration_for_stereo_buffer():
    _app()
    widget = AudioWaveformWidget()
    try:
        audio = np.zeros((8000, 2), dtype=np.float32)
        widget.set_audio(audio, 4000)

        assert widget._sample_rate == 4000
        assert widget._duration == 2.0
        assert widget._audio.shape == (8000, 2)
    finally:
        widget.close()
        sip.delete(widget)


def test_waveform_normalizes_reversed_selection():
    _app()
    widget = AudioWaveformWidget()
    try:
        widget.set_selection(5.0, 2.0)
        assert widget._selection == (2.0, 5.0)
    finally:
        widget.close()
        sip.delete(widget)


def test_waveform_time_and_x_mapping_roundtrip():
    _app()
    widget = AudioWaveformWidget()
    try:
        widget.resize(424, 220)
        widget.set_audio(np.zeros(1000, dtype=np.float32), 100)

        x = widget._time_to_x(5.0)
        seconds = widget._x_to_time(x)

        assert seconds == 5.0
    finally:
        widget.close()
        sip.delete(widget)


def test_waveform_active_range_uses_active_chunk_index():
    _app()
    widget = AudioWaveformWidget()
    try:
        ranges = [
            {"output_start": 0.0, "output_end": 1.0},
            {"output_start": 1.0, "output_end": 2.0},
        ]
        widget.set_chunk_ranges(ranges, 1)

        assert widget._active_range() == ranges[1]
    finally:
        widget.close()
        sip.delete(widget)


def test_waveform_left_click_emits_clicked_chunk_index():
    app = _app()
    widget = AudioWaveformWidget()
    try:
        widget.resize(424, 220)
        widget.set_audio(np.zeros(2000, dtype=np.float32), 1000)
        widget.set_chunk_ranges(
            [
                {"output_start": 0.0, "output_end": 1.0},
                {"output_start": 1.0, "output_end": 2.0},
            ],
            0,
        )
        clicked = []
        widget.chunk_clicked.connect(clicked.append)
        widget.show()
        app.processEvents()

        QTest.mouseClick(
            widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(int(widget._time_to_x(1.5)), widget.height() // 2),
        )

        assert clicked == [1]
    finally:
        widget.close()
        sip.delete(widget)
