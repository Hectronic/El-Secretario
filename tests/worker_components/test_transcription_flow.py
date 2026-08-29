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
from unittest.mock import MagicMock

from src.worker_components import transcription_flow


def test_compute_segment_progress_with_and_without_diarization():
    p_plain = transcription_flow.compute_segment_progress(5.0, 10.0, False)
    p_diar = transcription_flow.compute_segment_progress(5.0, 10.0, True)
    assert p_plain == 50
    assert p_diar == 40


def test_merge_segments_text_with_diarization_labels():
    segments = [
        SimpleNamespace(start=0.0, end=4.0, text="hola"),
        SimpleNamespace(start=4.0, end=8.0, text="mundo"),
    ]
    diarization = MagicMock()
    diarization.itertracks.return_value = [
        (SimpleNamespace(start=0.0, end=4.0), None, "S1"),
        (SimpleNamespace(start=4.0, end=8.0), None, "S2"),
    ]

    merged = transcription_flow.merge_segments_text(segments, diarization)
    assert "[S1]" in merged
    assert "[S2]" in merged
    assert "hola" in merged
    assert "mundo" in merged
