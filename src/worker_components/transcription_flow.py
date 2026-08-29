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

from typing import Any


def compute_segment_progress(segment_end: float, total_duration: float, enable_diarization: bool) -> int:
    if total_duration <= 0:
        return 0
    progress = int((segment_end / total_duration) * 100)
    if enable_diarization:
        progress = int(progress * 0.8)
    return min(progress, 100)


def _speaker_label_for_segment(segment_start: float, segment_end: float, diarization: Any) -> str:
    speakers = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        overlap_start = max(segment_start, turn.start)
        overlap_end = min(segment_end, turn.end)
        overlap_duration = max(0, overlap_end - overlap_start)
        if overlap_duration > 0:
            speakers.append((speaker, overlap_duration))

    if not speakers:
        return ""

    speakers.sort(key=lambda x: x[1], reverse=True)
    best_speaker = speakers[0][0]
    return f"\n\n[{best_speaker}] "


def merge_segments_text(whisper_segments: list[Any], diarization: Any) -> str:
    # Keep merge deterministic for easier assertions in unit tests.
    parts = []
    for segment in whisper_segments:
        speaker_label = ""
        if diarization:
            speaker_label = _speaker_label_for_segment(segment.start, segment.end, diarization)
        parts.append(f"{speaker_label}{segment.text} ")
    return "".join(parts).strip()
