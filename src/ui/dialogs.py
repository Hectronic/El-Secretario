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

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                             QDialogButtonBox, QLabel, QDialogButtonBox, QCompleter,
                             QDateEdit, QListWidget, QListWidgetItem, QCheckBox)
from PyQt6.QtCore import QSettings, QStringListModel, Qt, QDate

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 200)
        
        self.settings = QSettings("Hectronic", "Secretario")
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("hf_...")
        self.token_input.setText(self.settings.value("hf_token", ""))
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setPlaceholderText("AIza...")
        self.gemini_key_input.setText(self.settings.value("gemini_key", ""))
        self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addRow("Hugging Face Token:", self.token_input)
        form_layout.addRow("Gemini API Key:", self.gemini_key_input)
        layout.addLayout(form_layout)
        
        info_label = QLabel("HF Token: Required for Speaker Diarization.\n"
                            "Gemini Key: Required for Summarization and Cleanup (Google AI).")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def save_settings(self):
        self.settings.setValue("hf_token", self.token_input.text().strip())
        self.settings.setValue("gemini_key", self.gemini_key_input.text().strip())
        self.accept()

class SpeakerDialog(QDialog):
    def __init__(self, speakers, parent=None, known_speakers=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Speakers")
        self.resize(300, 400)
        self.speakers = speakers # List of speaker tags e.g. "SPEAKER_00"
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
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
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

class FilterDialog(QDialog):
    def __init__(self, all_tags, current_date=None, current_tags=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chat Filters")
        self.resize(300, 400)
        
        layout = QVBoxLayout(self)
        
        # Date Filter
        self.date_check = QCheckBox("Filter by Date")
        layout.addWidget(self.date_check)
        
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setEnabled(False)
        layout.addWidget(self.date_edit)
        
        self.date_check.toggled.connect(self.date_edit.setEnabled)
        
        if current_date:
            self.date_check.setChecked(True)
            self.date_edit.setDate(QDate.fromString(current_date, "yyyy-MM-dd"))
            
        # Tag Filter
        layout.addWidget(QLabel("Filter by Tags:"))
        self.tag_list = QListWidget()
        for tag in all_tags:
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if current_tags and tag in current_tags:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            self.tag_list.addItem(item)
        layout.addWidget(self.tag_list)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_filters(self):
        date_str = None
        if self.date_check.isChecked():
            date_str = self.date_edit.date().toString("yyyy-MM-dd")
            
        tags = []
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                tags.append(item.text())
                
        return {"date": date_str, "tags": tags}
