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

"""Dialog for remapping speaker labels in transcriptions."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)


class SpeakerDialog(QDialog):
    def __init__(self, speakers, parent=None, known_speakers=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Speakers")
        self.resize(300, 400)
        self.speakers = speakers
        self.mapping = {}

        layout = QVBoxLayout(self)
        self.inputs = {}

        form_layout = QFormLayout()
        for spk in self.speakers:
            edit = QLineEdit(spk)
            if known_speakers:
                completer = QCompleter(known_speakers)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                completer.setFilterMode(Qt.MatchFlag.MatchContains)
                edit.setCompleter(completer)

            self.inputs[spk] = edit
            form_layout.addRow(f"[{spk}]:", edit)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_mapping(self):
        mapping = {}
        for spk, edit in self.inputs.items():
            new_name = edit.text().strip()
            if new_name and new_name != spk:
                mapping[spk] = new_name
        return mapping
