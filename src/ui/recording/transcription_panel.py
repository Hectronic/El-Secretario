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

from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel

from src.transcription_options import DEFAULT_TRANSCRIPTION_MODEL, get_transcription_model_options
from src.ui.recording.controls import create_primary_action


@dataclass
class TranscriptionPanel:
    layout: QHBoxLayout
    model_combo: QComboBox
    lang_combo: QComboBox
    diarization_check: QCheckBox
    retranscribe_btn: object


def build_transcription_panel(parent, retranscribe_slot):
    layout = QHBoxLayout()
    layout.addWidget(QLabel("Retranscription Options:"))

    model_combo = QComboBox()
    model_combo.addItems(get_transcription_model_options())
    model_combo.setCurrentText(DEFAULT_TRANSCRIPTION_MODEL)
    layout.addWidget(QLabel("Model:"))
    layout.addWidget(model_combo)

    lang_combo = QComboBox()
    lang_combo.addItems(["Auto", "Spanish", "English"])
    layout.addWidget(QLabel("Language:"))
    layout.addWidget(lang_combo)

    diarization_check = QCheckBox("Diarization")
    diarization_check.setToolTip("Enable speaker diarization (Requires HF Token)")
    layout.addWidget(diarization_check)

    retranscribe_btn = create_primary_action(
        "Retranscribe",
        retranscribe_slot,
        min_height=34,
        enabled=False,
        parent=parent,
    )
    layout.addSpacing(10)
    layout.addWidget(retranscribe_btn)
    layout.addStretch()

    return TranscriptionPanel(
        layout=layout,
        model_combo=model_combo,
        lang_combo=lang_combo,
        diarization_check=diarization_check,
        retranscribe_btn=retranscribe_btn,
    )
