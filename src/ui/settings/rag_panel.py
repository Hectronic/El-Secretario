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

"""RAG runtime settings panel."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget


class RAGSettingsPanel(QWidget):
    """Panel for RAG engine runtime settings."""

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

        section_label = QLabel("🧠 RAG Engine Runtime")
        section_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #607D8B; margin-top: 10px;")
        form_layout.addRow(section_label)

        self.rag_enabled_check = QCheckBox("Enable RAG engine")
        self.rag_enabled_check.setChecked(self.settings.value("rag_enabled", True, type=bool))
        self.rag_enabled_check.setToolTip("If disabled, semantic chat/search based on RAG will be unavailable.")
        form_layout.addRow("RAG Enabled:", self.rag_enabled_check)

        self.persist_dir_input = QLineEdit()
        self.persist_dir_input.setText(self.settings.value("rag_persist_directory", "chroma_db"))
        self.persist_dir_input.setPlaceholderText("chroma_db")
        self.persist_dir_input.setToolTip("Directory where the vector database is stored.")
        form_layout.addRow("Persist Directory:", self.persist_dir_input)

        self.safe_delete_check = QCheckBox("Use safe delete mode")
        self.safe_delete_check.setChecked(self.settings.value("rag_safe_delete_mode", True, type=bool))
        self.safe_delete_check.setToolTip("Recommended on Windows to avoid native delete crashes.")
        form_layout.addRow("Safe Delete:", self.safe_delete_check)

        self.subprocess_upsert_check = QCheckBox("Use subprocess for upsert")
        self.subprocess_upsert_check.setChecked(self.settings.value("rag_subprocess_upsert_mode", True, type=bool))
        self.subprocess_upsert_check.setToolTip("Performs upserts in a subprocess for stability on some systems.")
        form_layout.addRow("Subprocess Upsert:", self.subprocess_upsert_check)

        self.subprocess_query_check = QCheckBox("Use subprocess for query")
        self.subprocess_query_check.setChecked(self.settings.value("rag_subprocess_query_mode", True, type=bool))
        self.subprocess_query_check.setToolTip("Performs vector queries in a subprocess for stability on some systems.")
        form_layout.addRow("Subprocess Query:", self.subprocess_query_check)

        layout.addLayout(form_layout)

        info_label = QLabel(
            "Initialize starts RAG using current options.\n"
            "Reload recreates the engine and reapplies runtime flags."
        )
        info_label.setStyleSheet("color: gray; font-size: 13px;")
        layout.addWidget(info_label)
        layout.addStretch()

    def get_rag_config(self):
        persist_directory = self.persist_dir_input.text().strip() or "chroma_db"
        return {
            "enabled": self.rag_enabled_check.isChecked(),
            "persist_directory": persist_directory,
            "safe_delete_mode": self.safe_delete_check.isChecked(),
            "subprocess_upsert_mode": self.subprocess_upsert_check.isChecked(),
            "subprocess_query_mode": self.subprocess_query_check.isChecked(),
        }

    def save(self):
        cfg = self.get_rag_config()
        self.settings.setValue("rag_enabled", cfg["enabled"])
        self.settings.setValue("rag_persist_directory", cfg["persist_directory"])
        self.settings.setValue("rag_safe_delete_mode", cfg["safe_delete_mode"])
        self.settings.setValue("rag_subprocess_upsert_mode", cfg["subprocess_upsert_mode"])
        self.settings.setValue("rag_subprocess_query_mode", cfg["subprocess_query_mode"])
