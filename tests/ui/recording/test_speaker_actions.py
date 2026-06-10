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
# along with this program.  See <https://www.gnu.org/licenses/>.

from src.ui.recording.speaker_actions import apply_speaker_mapping, find_speaker_labels


def test_find_speaker_labels_returns_sorted_unique_labels():
    text = "SPEAKER_02: Later\nSPEAKER_01: Hi\nSPEAKER_02: Again"

    assert find_speaker_labels(text) == ["SPEAKER_01", "SPEAKER_02"]


def test_find_speaker_labels_ignores_empty_text():
    assert find_speaker_labels("") == []
    assert find_speaker_labels(None) == []


def test_apply_speaker_mapping_replaces_all_labels():
    text = "SPEAKER_00: Hello\nSPEAKER_01: Hi\nSPEAKER_00: Bye"

    assert apply_speaker_mapping(text, {"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"}) == (
        "Alice: Hello\nBob: Hi\nAlice: Bye"
    )
