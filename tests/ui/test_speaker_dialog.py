# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

from src.ui.speaker_dialog import SpeakerDialog


def test_speaker_dialog_returns_mapping_for_renamed_speakers(qtbot):
    dialog = SpeakerDialog(["SPEAKER_00", "SPEAKER_01"], known_speakers=["Alice", "Bob"])
    qtbot.addWidget(dialog)

    dialog.inputs["SPEAKER_00"].setText("Alice")
    dialog.inputs["SPEAKER_01"].setText("SPEAKER_01")

    assert dialog.get_mapping() == {"SPEAKER_00": "Alice"}


def test_speaker_dialog_keeps_original_labels_when_empty(qtbot):
    dialog = SpeakerDialog(["SPEAKER_00"])
    qtbot.addWidget(dialog)

    dialog.inputs["SPEAKER_00"].setText("")

    assert dialog.get_mapping() == {}
