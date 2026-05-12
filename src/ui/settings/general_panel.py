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

"""General application settings panel."""

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.secret_field_widget import SecretFieldWidget
from src.ui.styles import apply_theme


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

        hf_val = self.settings.value("hf_token", "")
        self.hf_container, self.token_input = self._create_token_field(hf_val, "hf_...")

        lbl_hf = QLabel("Hugging Face Token:")
        lbl_hf.setStyleSheet("font-weight: bold;")
        form_layout.addRow(lbl_hf, self.hf_container)

        ai_section_label = QLabel("🤖 AI Provider")
        ai_section_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #607D8B; margin-top: 20px;")
        form_layout.addRow(ai_section_label)

        lbl_provider = QLabel("AI Provider:")
        lbl_provider.setStyleSheet("font-weight: bold;")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Google Gemini", "Ollama (Local)"])
        current_provider = self.settings.value("ai_provider", "gemini")
        self.provider_combo.setCurrentIndex(0 if current_provider == "gemini" else 1)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        form_layout.addRow(lbl_provider, self.provider_combo)

        self.gemini_widget = QWidget()
        gemini_layout = QFormLayout(self.gemini_widget)
        gemini_layout.setContentsMargins(0, 0, 0, 0)

        gemini_val = self.settings.value("gemini_key", "")
        self.gemini_container, self.gemini_key_input = self._create_token_field(gemini_val, "AIza...")
        lbl_gemini = QLabel("Gemini API Key:")
        lbl_gemini.setStyleSheet("font-weight: bold;")
        gemini_layout.addRow(lbl_gemini, self.gemini_container)

        lbl_gemini_model = QLabel("Gemini Model:")
        lbl_gemini_model.setStyleSheet("font-weight: bold;")
        self.gemini_model_combo = QComboBox()
        self.gemini_model_combo.addItems(["gemini-3-flash-preview", "gemini-3-preview"])
        self.gemini_model_combo.setCurrentText(self.settings.value("gemini_model", "gemini-3-flash-preview"))
        gemini_layout.addRow(lbl_gemini_model, self.gemini_model_combo)

        form_layout.addRow(self.gemini_widget)

        self.ollama_widget = QWidget()
        ollama_layout = QFormLayout(self.ollama_widget)
        ollama_layout.setContentsMargins(0, 0, 0, 0)

        lbl_ollama_host = QLabel("Ollama Server:")
        lbl_ollama_host.setStyleSheet("font-weight: bold;")
        self.ollama_host_input = QLineEdit()
        self.ollama_host_input.setPlaceholderText("http://localhost:11434")
        self.ollama_host_input.setText(self.settings.value("ollama_host", "http://localhost:11434"))
        ollama_layout.addRow(lbl_ollama_host, self.ollama_host_input)

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

        self.ollama_status_label = QLabel("")
        self.ollama_status_label.setStyleSheet("color: gray; font-size: 12px;")
        ollama_layout.addRow("", self.ollama_status_label)

        form_layout.addRow(self.ollama_widget)

        lbl_theme = QLabel("Interface Theme:")
        lbl_theme.setStyleSheet("font-weight: bold;")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark", "SNES"])
        self.theme_combo.setCurrentText(self.settings.value("app_theme", "System"))
        form_layout.addRow(lbl_theme, self.theme_combo)

        lbl_lang = QLabel("System Language:")
        lbl_lang.setStyleSheet("font-weight: bold;")
        self.lang_input = QLineEdit()
        self.lang_input.setPlaceholderText("e.g. Spanish, English, ES, EN")
        self.lang_input.setText(self.settings.value("system_language", "Spanish"))
        self.lang_input.setToolTip("The language the AI will use for daily and weekly summaries.")
        form_layout.addRow(lbl_lang, self.lang_input)

        lbl_startup_weekly = QLabel("Startup Weekly Summary:")
        lbl_startup_weekly.setStyleSheet("font-weight: bold;")
        self.startup_last_weekly_check = QCheckBox("Auto-enqueue last week summary if missing")
        self.startup_last_weekly_check.setChecked(
            self.settings.value("startup_enqueue_last_weekly_summary", False, type=bool)
        )
        self.startup_last_weekly_check.setToolTip(
            "On app startup, if last week's summary doesn't exist, queue it automatically."
        )
        form_layout.addRow(lbl_startup_weekly, self.startup_last_weekly_check)

        lbl_startup_daily = QLabel("Startup Daily Summary:")
        lbl_startup_daily.setStyleSheet("font-weight: bold;")
        self.startup_prev_daily_check = QCheckBox("Auto-enqueue latest missing previous daily summary")
        self.startup_prev_daily_check.setChecked(
            self.settings.value("startup_enqueue_previous_daily_summary", False, type=bool)
        )
        self.startup_prev_daily_check.setToolTip(
            "On startup, find the most recent earlier day with recordings and no daily summary, then queue it."
        )
        form_layout.addRow(lbl_startup_daily, self.startup_prev_daily_check)

        layout.addLayout(form_layout)

        info_label = QLabel(
            "HF Token: Required for Speaker Diarization.\n"
            "AI Provider: Choose between Google Gemini (cloud) or Ollama (local LLM)."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 13px; margin-top: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()

        self._on_provider_changed()

    def _on_provider_changed(self):
        """Show/hide provider-specific settings based on selection."""
        is_gemini = self.provider_combo.currentIndex() == 0
        self.gemini_widget.setVisible(is_gemini)
        self.ollama_widget.setVisible(not is_gemini)

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
        """Create a reusable secret field and expose its line edit for save/load."""
        field = SecretFieldWidget(current_value=current_value, placeholder=placeholder)
        return field, field.line_edit

    def save(self):
        """Save general settings."""
        self.settings.setValue("hf_token", self.token_input.text().strip())
        self.settings.setValue("gemini_key", self.gemini_key_input.text().strip())
        self.settings.setValue("gemini_model", self.gemini_model_combo.currentText())

        provider = "gemini" if self.provider_combo.currentIndex() == 0 else "ollama"
        self.settings.setValue("ai_provider", provider)

        self.settings.setValue("ollama_host", self.ollama_host_input.text().strip() or "http://localhost:11434")
        if self.ollama_model_combo.currentText():
            self.settings.setValue("ollama_model", self.ollama_model_combo.currentText())

        selected_theme = self.theme_combo.currentText()
        self.settings.setValue("app_theme", selected_theme)
        self.settings.setValue("system_language", self.lang_input.text().strip() or "Spanish")
        self.settings.setValue(
            "startup_enqueue_last_weekly_summary",
            self.startup_last_weekly_check.isChecked(),
        )
        self.settings.setValue(
            "startup_enqueue_previous_daily_summary",
            self.startup_prev_daily_check.isChecked(),
        )
        apply_theme(selected_theme)
