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
                             QHBoxLayout, QApplication, QTabWidget, QTextEdit, QScrollArea)
from PyQt6.QtCore import QSettings, QStringListModel, Qt, QDate, QTimer
from src.ui.styles import apply_theme

# Default prompts for AI tasks
DEFAULT_PROMPTS = {
    "summary": """Please provide a concise and structured summary of the following transcription.
Highlight key points, decisions made, and action items if any.
Maintain the original language of the transcription.

Transcription:
{text}""",
    "clean": """Please clean up the following transcription.
- Fix grammatical errors and punctuation.
- Remove filler words (uh, um, like).
- Improve readability while maintaining the original meaning and tone.
- Do NOT summarize, keep the full content.
- Maintain the original language of the transcription.

Transcription:
{text}""",
    "daily_summary": """As an expert assistant, provide a concise and structured daily summary based on the following recording summaries from today.
Group key information by topic, highlight important decisions, and list any pending action items.
The summary MUST be written in {language}.

Meeting Summaries:
{text}""",
    "weekly_summary": """As an expert assistant, provide a comprehensive and professional weekly summary based on the following recording content from this week.
Organize the summary by topic or day, highlighting key achievements, strategic decisions, and future action items.
The summary MUST be written in {language}.

Recordings Content:
{text}""",
    "task_extraction": """Extract actionable tasks and to-do items from the transcription provided below.

Rules:
- Format: A simple JSON array of strings.
- Example: ["Task 1", "Task 2"]
- If no tasks are found, return [].
- Language: {language}
- Output ONLY the JSON array. Do not include markdown code blocks or any other text.

Transcription:
<transcription>
{text}
</transcription>

JSON:"""
}


class GeneralSettingsPanel(QWidget):
    """Panel for general application settings."""
    
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # HF Token
        hf_val = self.settings.value("hf_token", "")
        self.hf_container, self.token_input = self._create_token_field(hf_val, "hf_...")
        
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
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        form_layout.addRow(lbl_provider, self.provider_combo)
        
        # Gemini Settings Container
        self.gemini_widget = QWidget()
        gemini_layout = QFormLayout(self.gemini_widget)
        gemini_layout.setContentsMargins(0, 0, 0, 0)
        
        gemini_val = self.settings.value("gemini_key", "")
        self.gemini_container, self.gemini_key_input = self._create_token_field(gemini_val, "AIza...")
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
        self.refresh_ollama_btn.clicked.connect(self._refresh_ollama_models)
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
        self.theme_combo.addItems(["System", "Light", "Dark", "SNES"])
        self.theme_combo.setCurrentText(self.settings.value("app_theme", "System"))
        form_layout.addRow(lbl_theme, self.theme_combo)

        # System Language Setting
        lbl_lang = QLabel("System Language:")
        lbl_lang.setStyleSheet("font-weight: bold;")
        self.lang_input = QLineEdit()
        self.lang_input.setPlaceholderText("e.g. Spanish, English, ES, EN")
        self.lang_input.setText(self.settings.value("system_language", "Spanish"))
        self.lang_input.setToolTip("The language the AI will use for daily and weekly summaries.")
        form_layout.addRow(lbl_lang, self.lang_input)
        
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
        
        layout.addStretch()
        
        # Initialize visibility
        self._on_provider_changed()
    
    def _on_provider_changed(self):
        """Show/hide provider-specific settings based on selection."""
        is_gemini = self.provider_combo.currentIndex() == 0
        self.gemini_widget.setVisible(is_gemini)
        self.ollama_widget.setVisible(not is_gemini)
        
        # Auto-refresh Ollama models when switching to Ollama
        if not is_gemini and self.ollama_model_combo.count() <= 1:
            QTimer.singleShot(100, self._refresh_ollama_models)

    def _refresh_ollama_models(self):
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
    
    def _create_token_field(self, current_value, placeholder):
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
            
        copy_btn.clicked.connect(copy_text)

        layout.addWidget(line_edit)
        layout.addWidget(show_btn)
        layout.addWidget(copy_btn)
        
        return container, line_edit
    
    def save(self):
        """Save general settings."""
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
        self.settings.setValue("system_language", self.lang_input.text().strip() or "Spanish")
        # Backward compatibility: some UI variants may not expose whisper model selector.
        if hasattr(self, "whisper_model_combo") and self.whisper_model_combo is not None:
            self.settings.setValue("whisper_model", self.whisper_model_combo.currentText())
        elif self.settings.value("whisper_model", "") in (None, ""):
            self.settings.setValue("whisper_model", "base")
        self.settings.setValue("force_cpu", self.force_cpu_check.isChecked())
        self.settings.setValue("compute_type", self.compute_combo.currentText())
        apply_theme(selected_theme)


class PromptsSettingsPanel(QWidget):
    """Panel for customizing AI prompts."""
    
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.prompt_editors = {}
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Info label
        info_label = QLabel("✏️ Customize the prompts used by the AI assistant. "
                           "Use {text} as a placeholder for the transcription content.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #607D8B; font-size: 13px; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # Create editors for each prompt type
        prompt_configs = [
            ("summary", "📝 Summary Prompt", "Used when generating a summary of a transcription."),
            ("clean", "🧹 Clean Prompt", "Used when cleaning up a transcription."),
            ("daily_summary", "📅 Daily Summary Prompt", "Used when generating a daily summary from recording summaries."),
            ("weekly_summary", "📅 Weekly Summary Prompt", "Used when generating a weekly summary."),
            ("task_extraction", "✅ Task Extraction Prompt", "Used to extract a JSON list of tasks from a transcription."),
        ]
        
        for prompt_key, title, description in prompt_configs:
            self._add_prompt_editor(layout, prompt_key, title, description)
        
        # Reset to defaults button
        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.setFixedWidth(150)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        reset_btn.clicked.connect(self._reset_to_defaults)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
    
    def _add_prompt_editor(self, parent_layout, prompt_key, title, description):
        """Add a prompt editor section."""
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #607D8B; margin-top: 10px;")
        parent_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: gray; font-size: 12px;")
        parent_layout.addWidget(desc_label)
        
        # Text editor - uses global theme styles, just set font
        editor = QTextEdit()
        editor.setMinimumHeight(100)
        editor.setMaximumHeight(150)
        editor.setStyleSheet("font-family: monospace; font-size: 12px;")
        
        # Load saved prompt or default
        saved_prompt = self.settings.value(f"prompt_{prompt_key}", DEFAULT_PROMPTS.get(prompt_key, ""))
        editor.setPlainText(saved_prompt)
        
        parent_layout.addWidget(editor)
        self.prompt_editors[prompt_key] = editor
    
    def _reset_to_defaults(self):
        """Reset all prompts to their default values."""
        for prompt_key, editor in self.prompt_editors.items():
            default_prompt = DEFAULT_PROMPTS.get(prompt_key, "")
            editor.setPlainText(default_prompt)
    
    def save(self):
        """Save all prompts to settings."""
        for prompt_key, editor in self.prompt_editors.items():
            self.settings.setValue(f"prompt_{prompt_key}", editor.toPlainText())


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
        
        # Tab Widget - uses global theme styles
        self.tab_widget = QTabWidget()
        
        # General Settings Panel
        self.general_panel = GeneralSettingsPanel(self.settings)
        scroll_general = QScrollArea()
        scroll_general.setWidget(self.general_panel)
        scroll_general.setWidgetResizable(True)
        scroll_general.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tab_widget.addTab(scroll_general, "🔧 General")
        
        # Prompts Settings Panel
        self.prompts_panel = PromptsSettingsPanel(self.settings)
        scroll_prompts = QScrollArea()
        scroll_prompts.setWidget(self.prompts_panel)
        scroll_prompts.setWidgetResizable(True)
        scroll_prompts.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tab_widget.addTab(scroll_prompts, "💬 Prompts")
        
        layout.addWidget(self.tab_widget)
        
        # Status Label for feedback
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Save button
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

    def save_settings(self):
        """Save all settings from both panels."""
        self.general_panel.save()
        self.prompts_panel.save()
        
        self.status_label.setText("✅ Settings saved successfully!")
        QTimer.singleShot(3000, self._clear_status_label)
    
    def _clear_status_label(self):
        """Safely clear the status label."""
        try:
            if self.status_label:
                self.status_label.setText("")
        except RuntimeError:
            pass  # Widget was already deleted

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
