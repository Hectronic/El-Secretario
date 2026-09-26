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

from bisect import bisect_left
from typing import Any


def compute_segment_progress(segment_end: float, total_duration: float, enable_diarization: bool) -> int:
    if total_duration <= 0:
        return 0
    progress = int((segment_end / total_duration) * 100)
    if enable_diarization:
        progress = int(progress * 0.8)
    return min(progress, 100)


class _DiarizationIntervalIndex:
    """Index diarization turns so transcript segments only inspect overlaps."""

    def __init__(self, diarization: Any):
        turns = []
        for order, (turn, _, speaker) in enumerate(diarization.itertracks(yield_label=True)):
            start, end = float(turn.start), float(turn.end)
            if end > start:
                turns.append((start, end, speaker, order))

        turns.sort(key=lambda item: (item[0], item[3]))
        self.turns = turns
        self.starts = [turn[0] for turn in turns]
        self.prefix_max_ends = []
        max_end = float("-inf")
        for _start, end, _speaker, _order in turns:
            max_end = max(max_end, end)
            self.prefix_max_ends.append(max_end)

    def label_for(self, segment_start: float, segment_end: float) -> str:
        if segment_end <= segment_start or not self.turns:
            return ""

        # Only turns starting before the segment end can overlap it. Walking
        # backwards lets prefix_max_ends skip whole regions that have already
        # ended, instead of rescanning every diarization turn per segment.
        index = bisect_left(self.starts, segment_end) - 1
        best_speaker = None
        best_duration = 0.0
        best_order = float("inf")
        while index >= 0 and self.prefix_max_ends[index] > segment_start:
            turn_start, turn_end, speaker, order = self.turns[index]
            overlap = min(segment_end, turn_end) - max(segment_start, turn_start)
            if overlap > best_duration or (overlap == best_duration and overlap > 0 and order < best_order):
                best_speaker = speaker
                best_duration = overlap
                best_order = order
            index -= 1

        return f"\n\n[{best_speaker}] " if best_speaker is not None else ""


def merge_segments_text(whisper_segments: list[Any], diarization: Any) -> str:
    # Keep merge deterministic for easier assertions in unit tests.
    parts = []
    interval_index = _DiarizationIntervalIndex(diarization) if diarization else None
    for segment in whisper_segments:
        speaker_label = ""
        if interval_index:
            speaker_label = interval_index.label_for(segment.start, segment.end)
        parts.append(f"{speaker_label}{segment.text} ")
    return "".join(parts).strip()
