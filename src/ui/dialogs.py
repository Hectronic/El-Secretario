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
                             QDialogButtonBox, QLabel, QWidget, QPushButton, QCompleter,
                             QDateEdit, QListWidget, QListWidgetItem, QCheckBox, QComboBox,
                             QHBoxLayout, QApplication)
from PyQt6.QtCore import QSettings, QStringListModel, Qt, QDate, QTimer
from src.ui.styles import apply_theme

class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("Hectronic", "Secretario")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("⚙️ Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #607D8B;")
        layout.addWidget(title)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # HF Token
        hf_val = self.settings.value("hf_token", "")
        self.hf_container, self.token_input = self.create_token_field(hf_val, "hf_...")
        
        lbl_hf = QLabel("Hugging Face Token:")
        lbl_hf.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_hf, self.hf_container)
        
        # --- AI Provider Section ---
        ai_section_label = QLabel("🤖 AI Provider")
        ai_section_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #607D8B; margin-top: 20px;")
        form_layout.addRow(ai_section_label)
        
        # AI Provider Selector
        lbl_provider = QLabel("AI Provider:")
        lbl_provider.setStyleSheet("font-weight: bold;")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Google Gemini", "Ollama (Local)"])
        current_provider = self.settings.value("ai_provider", "gemini")
        self.provider_combo.setCurrentIndex(0 if current_provider == "gemini" else 1)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        form_layout.addRow(lbl_provider, self.provider_combo)
        
        # Gemini Settings Container
        self.gemini_widget = QWidget()
        gemini_layout = QFormLayout(self.gemini_widget)
        gemini_layout.setContentsMargins(0, 0, 0, 0)
        
        gemini_val = self.settings.value("gemini_key", "")
        self.gemini_container, self.gemini_key_input = self.create_token_field(gemini_val, "AIza...")
        lbl_gemini = QLabel("Gemini API Key:")
        lbl_gemini.setStyleSheet("font-weight: bold;")
        gemini_layout.addRow(lbl_gemini, self.gemini_container)
        
        # Gemini Model Selector
        lbl_gemini_model = QLabel("Gemini Model:")
        lbl_gemini_model.setStyleSheet("font-weight: bold;")
        self.gemini_model_combo = QComboBox()
        self.gemini_model_combo.addItems(["gemini-3-flash-preview", "gemini-3-preview"])
        self.gemini_model_combo.setCurrentText(self.settings.value("gemini_model", "gemini-3-flash-preview"))
        gemini_layout.addRow(lbl_gemini_model, self.gemini_model_combo)
        
        form_layout.addRow(self.gemini_widget)
        
        # Ollama Settings Container
        self.ollama_widget = QWidget()
        ollama_layout = QFormLayout(self.ollama_widget)
        ollama_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_ollama_host = QLabel("Ollama Server:")
        lbl_ollama_host.setStyleSheet("font-weight: bold;")
        self.ollama_host_input = QLineEdit()
        self.ollama_host_input.setPlaceholderText("http://localhost:11434")
        self.ollama_host_input.setText(self.settings.value("ollama_host", "http://localhost:11434"))
        ollama_layout.addRow(lbl_ollama_host, self.ollama_host_input)
        
        # Ollama Model Selector with Refresh
        lbl_ollama_model = QLabel("Ollama Model:")
        lbl_ollama_model.setStyleSheet("font-weight: bold;")
        ollama_model_container = QWidget()
        ollama_model_layout = QHBoxLayout(ollama_model_container)
        ollama_model_layout.setContentsMargins(0, 0, 0, 0)
        
        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setMinimumWidth(200)
        saved_model = self.settings.value("ollama_model", "")
        if saved_model:
            self.ollama_model_combo.addItem(saved_model)
        ollama_model_layout.addWidget(self.ollama_model_combo)
        
        self.refresh_ollama_btn = QPushButton("🔄 Refresh")
        self.refresh_ollama_btn.setFixedWidth(80)
        self.refresh_ollama_btn.clicked.connect(self.refresh_ollama_models)
        ollama_model_layout.addWidget(self.refresh_ollama_btn)
        
        ollama_layout.addRow(lbl_ollama_model, ollama_model_container)
        
        # Ollama Status
        self.ollama_status_label = QLabel("")
        self.ollama_status_label.setStyleSheet("color: gray; font-size: 12px;")
        ollama_layout.addRow("", self.ollama_status_label)
        
        form_layout.addRow(self.ollama_widget)
        
        # Theme Setting
        lbl_theme = QLabel("Interface Theme:")
        lbl_theme.setStyleSheet("font-weight: bold;")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        self.theme_combo.setCurrentText(self.settings.value("app_theme", "System"))
        form_layout.addRow(lbl_theme, self.theme_combo)
        
        # Force CPU Setting
        lbl_force_cpu = QLabel("Force CPU:")
        lbl_force_cpu.setStyleSheet("font-weight: bold;")
        self.force_cpu_check = QCheckBox("Disable GPU acceleration")
        self.force_cpu_check.setToolTip("Force transcription and diarization to use CPU even if GPU is available")
        self.force_cpu_check.setChecked(self.settings.value("force_cpu", False, type=bool))
        form_layout.addRow(lbl_force_cpu, self.force_cpu_check)
        
        # Compute Type Setting
        lbl_compute = QLabel("Compute Type:")
        lbl_compute.setStyleSheet("font-weight: bold;")
        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["auto", "int8", "int8_float16", "float16", "float32"])
        self.compute_combo.setCurrentText(self.settings.value("compute_type", "int8"))
        self.compute_combo.setToolTip(
            "int8: Best for GPUs with limited VRAM (6-8GB), fastest\n"
            "int8_float16: Hybrid precision, good balance\n"
            "float16: Better quality, needs more VRAM\n"
            "float32: Highest quality, needs most VRAM\n"
            "auto: Let the app decide based on your GPU"
        )
        form_layout.addRow(lbl_compute, self.compute_combo)
        
        layout.addLayout(form_layout)
        
        info_label = QLabel("HF Token: Required for Speaker Diarization.\n"
                            "AI Provider: Choose between Google Gemini (cloud) or Ollama (local LLM).")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 13px; margin-top: 10px;")
        layout.addWidget(info_label)
        
        # Status Label for feedback
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        save_btn = QPushButton("Save Settings")
        save_btn.setFixedSize(150, 40)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        # Initialize visibility
        self.on_provider_changed()

    def on_provider_changed(self):
        """Show/hide provider-specific settings based on selection."""
        is_gemini = self.provider_combo.currentIndex() == 0
        self.gemini_widget.setVisible(is_gemini)
        self.ollama_widget.setVisible(not is_gemini)
        
        # Auto-refresh Ollama models when switching to Ollama
        if not is_gemini and self.ollama_model_combo.count() <= 1:
            QTimer.singleShot(100, self.refresh_ollama_models)

    def refresh_ollama_models(self):
        """Fetch available models from Ollama server."""
        self.ollama_status_label.setText("Fetching models...")
        self.ollama_status_label.setStyleSheet("color: gray; font-size: 12px;")
        QApplication.processEvents()
        
        try:
            from src.ai_provider import get_available_ollama_models, is_ollama_available
            
            host = self.ollama_host_input.text().strip() or "http://localhost:11434"
            
            if not is_ollama_available(host):
                self.ollama_status_label.setText("⚠️ Ollama not running. Start it with: ollama serve")
                self.ollama_status_label.setStyleSheet("color: orange; font-size: 12px;")
                return
            
            models = get_available_ollama_models(host)
            
            current_model = self.ollama_model_combo.currentText()
            self.ollama_model_combo.clear()
            
            if models:
                self.ollama_model_combo.addItems(models)
                if current_model in models:
                    self.ollama_model_combo.setCurrentText(current_model)
                self.ollama_status_label.setText(f"✅ Found {len(models)} models")
                self.ollama_status_label.setStyleSheet("color: green; font-size: 12px;")
            else:
                self.ollama_status_label.setText("⚠️ No models found. Install one with: ollama pull llama3")
                self.ollama_status_label.setStyleSheet("color: orange; font-size: 12px;")
                
        except Exception as e:
            self.ollama_status_label.setText(f"❌ Error: {str(e)[:50]}")
            self.ollama_status_label.setStyleSheet("color: red; font-size: 12px;")

    def create_token_field(self, current_value, placeholder):
        """Creates a hidden input field with Show/Hide and Copy buttons."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setText(current_value)
        line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        line_edit.setMinimumWidth(350) 
        
        # Show/Hide Button
        show_btn = QPushButton("👁️")
        show_btn.setToolTip("Show/Hide Token")
        show_btn.setFixedSize(30, 30)
        show_btn.setCheckable(True)
        
        def toggle_echo():
            if show_btn.isChecked():
                line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
                show_btn.setText("🔒")
            else:
                line_edit.setEchoMode(QLineEdit.EchoMode.Password)
                show_btn.setText("👁️")
        
        show_btn.clicked.connect(toggle_echo)

        # Copy Button
        copy_btn = QPushButton("📋") 
        copy_btn.setToolTip("Copy Token")
        copy_btn.setFixedSize(30, 30)
        
        def copy_text():
            clipboard = QApplication.clipboard()
            clipboard.setText(line_edit.text())
            # Optional: Visual feedback could be added here
            
        copy_btn.clicked.connect(copy_text)

        layout.addWidget(line_edit)
        layout.addWidget(show_btn)
        layout.addWidget(copy_btn)
        
        return container, line_edit

    def save_settings(self):
        self.settings.setValue("hf_token", self.token_input.text().strip())
        
        # Always save Gemini key (even when using Ollama, to preserve it)
        self.settings.setValue("gemini_key", self.gemini_key_input.text().strip())
        self.settings.setValue("gemini_model", self.gemini_model_combo.currentText())
        
        # Save AI provider selection
        provider = "gemini" if self.provider_combo.currentIndex() == 0 else "ollama"
        self.settings.setValue("ai_provider", provider)
        
        # Save Ollama settings
        self.settings.setValue("ollama_host", self.ollama_host_input.text().strip() or "http://localhost:11434")
        if self.ollama_model_combo.currentText():
            self.settings.setValue("ollama_model", self.ollama_model_combo.currentText())
        
        selected_theme = self.theme_combo.currentText()
        self.settings.setValue("app_theme", selected_theme)
        self.settings.setValue("force_cpu", self.force_cpu_check.isChecked())
        self.settings.setValue("compute_type", self.compute_combo.currentText())
        apply_theme(selected_theme)
        
        self.status_label.setText("✅ Settings saved successfully!")
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

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
