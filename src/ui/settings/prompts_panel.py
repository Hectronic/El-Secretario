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

"""Prompt customization settings panel."""

from PyQt6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from src.ui.settings.prompts_defaults import DEFAULT_PROMPTS


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

        info_label = QLabel(
            "✏️ Customize the prompts used by the AI assistant. "
            "Use {text} as a placeholder for the transcription content."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #607D8B; font-size: 13px; margin-bottom: 10px;")
        layout.addWidget(info_label)

        prompt_configs = [
            ("summary", "📝 Summary Prompt", "Used when generating a summary of a transcription."),
            ("clean", "🧹 Clean Prompt", "Used when cleaning up a transcription."),
            ("daily_summary", "📅 Daily Summary Prompt", "Used when generating a daily summary from recording summaries."),
            ("weekly_summary", "📅 Weekly Summary Prompt", "Used when generating a weekly summary."),
            ("task_extraction", "✅ Task Extraction Prompt", "Used to extract a JSON list of tasks from a transcription."),
        ]

        for prompt_key, title, description in prompt_configs:
            self._add_prompt_editor(layout, prompt_key, title, description)

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
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #607D8B; margin-top: 10px;")
        parent_layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: gray; font-size: 12px;")
        parent_layout.addWidget(desc_label)

        editor = QTextEdit()
        editor.setMinimumHeight(100)
        editor.setMaximumHeight(150)
        editor.setStyleSheet("font-family: monospace; font-size: 12px;")

        saved_prompt = self.settings.value(f"prompt_{prompt_key}", DEFAULT_PROMPTS.get(prompt_key, ""))
        editor.setPlainText(saved_prompt)

        parent_layout.addWidget(editor)
        self.prompt_editors[prompt_key] = editor

    def _reset_to_defaults(self):
        """Reset all prompts to their default values."""
        for prompt_key, editor in self.prompt_editors.items():
            editor.setPlainText(DEFAULT_PROMPTS.get(prompt_key, ""))

    def save(self):
        """Save all prompts to settings."""
        for prompt_key, editor in self.prompt_editors.items():
            self.settings.setValue(f"prompt_{prompt_key}", editor.toPlainText())
