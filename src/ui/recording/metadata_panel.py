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

from dataclasses import dataclass

from PyQt6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QLabel, QLineEdit

from src.ui.components import TagsLineEdit


@dataclass
class MetadataPanel:
    group: QGroupBox
    title_input: QLineEdit
    date_label: QLabel
    duration_label: QLabel
    tags_input: TagsLineEdit
    is_diarized_check: QCheckBox


def build_metadata_panel(all_tags):
    group = QGroupBox("Recording Details")
    layout = QFormLayout()

    title_input = QLineEdit()
    title_input.setPlaceholderText("Enter title...")
    title_input.setEnabled(False)
    layout.addRow("Title:", title_input)

    date_label = QLabel("-")
    layout.addRow("Date/Time:", date_label)

    duration_label = QLabel("-")
    layout.addRow("Duration:", duration_label)

    tags_input = TagsLineEdit()
    tags_input.setEnabled(False)
    tags_input.set_tags(all_tags)
    layout.addRow("Tags:", tags_input)

    is_diarized_check = QCheckBox("Diarized")
    is_diarized_check.setEnabled(False)
    layout.addRow("", is_diarized_check)

    group.setLayout(layout)
    return MetadataPanel(
        group=group,
        title_input=title_input,
        date_label=date_label,
        duration_label=duration_label,
        tags_input=tags_input,
        is_diarized_check=is_diarized_check,
    )
