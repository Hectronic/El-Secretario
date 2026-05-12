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

"""Settings widget that assembles the settings panels."""

from PyQt6.QtCore import QSettings, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.filter_dialog import FilterDialog
from src.ui.speaker_dialog import SpeakerDialog
from src.ui.settings.audio_panel import AudioSettingsPanel
from src.ui.settings.general_panel import GeneralSettingsPanel
from src.ui.settings.prompts_panel import PromptsSettingsPanel
from src.ui.settings.rag_panel import RAGSettingsPanel


class SettingsWidget(QWidget):
    rag_initialize_requested = pyqtSignal(dict)
    rag_reload_requested = pyqtSignal(dict)
    rag_reindex_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("Hectronic", "Secretario")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        title = QLabel("⚙️ Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #607D8B;")
        layout.addWidget(title)

        self.tab_widget = QTabWidget()

        self.general_panel = GeneralSettingsPanel(self.settings)
        scroll_general = QScrollArea()
        scroll_general.setWidget(self.general_panel)
        scroll_general.setWidgetResizable(True)
        scroll_general.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_general.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_general.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tab_widget.addTab(scroll_general, "🔧 General")

        self.audio_panel = AudioSettingsPanel(self.settings)
        scroll_audio = QScrollArea()
        scroll_audio.setWidget(self.audio_panel)
        scroll_audio.setWidgetResizable(True)
        scroll_audio.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_audio.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_audio.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tab_widget.addTab(scroll_audio, "🔊 Audio")

        self.rag_panel = RAGSettingsPanel(self.settings)
        scroll_rag = QScrollArea()
        scroll_rag.setWidget(self.rag_panel)
        scroll_rag.setWidgetResizable(True)
        scroll_rag.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_rag.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_rag.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tab_widget.addTab(scroll_rag, "🧠 RAG")

        self.prompts_panel = PromptsSettingsPanel(self.settings)
        scroll_prompts = QScrollArea()
        scroll_prompts.setWidget(self.prompts_panel)
        scroll_prompts.setWidgetResizable(True)
        scroll_prompts.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_prompts.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_prompts.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tab_widget.addTab(scroll_prompts, "💬 Prompts")

        layout.addWidget(self.tab_widget)

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

        rag_actions_layout = QHBoxLayout()
        self.rag_init_btn = QPushButton("Initialize RAG")
        self.rag_init_btn.clicked.connect(self._initialize_rag)
        rag_actions_layout.addWidget(self.rag_init_btn)

        self.rag_reload_btn = QPushButton("Reload RAG")
        self.rag_reload_btn.clicked.connect(self._reload_rag)
        rag_actions_layout.addWidget(self.rag_reload_btn)

        self.rag_reindex_btn = QPushButton("Queue RAG Reindex")
        self.rag_reindex_btn.clicked.connect(self._queue_rag_reindex)
        rag_actions_layout.addWidget(self.rag_reindex_btn)
        rag_actions_layout.addStretch()
        layout.addLayout(rag_actions_layout)

    def save_settings(self):
        """Save all settings from both panels."""
        self.general_panel.save()
        self.audio_panel.save()
        self.rag_panel.save()
        self.prompts_panel.save()
        self.settings.sync()

        self.status_label.setText("✅ Settings saved successfully!")
        QTimer.singleShot(3000, self._clear_status_label)

    def _initialize_rag(self):
        self.rag_panel.save()
        self.settings.sync()
        cfg = self.rag_panel.get_rag_config()
        self.rag_initialize_requested.emit(cfg)
        self.status_label.setText("RAG initialize requested.")
        QTimer.singleShot(3000, self._clear_status_label)

    def _reload_rag(self):
        self.rag_panel.save()
        self.settings.sync()
        cfg = self.rag_panel.get_rag_config()
        self.rag_reload_requested.emit(cfg)
        self.status_label.setText("RAG reload requested.")
        QTimer.singleShot(3000, self._clear_status_label)

    def _queue_rag_reindex(self):
        self.rag_reindex_requested.emit()
        self.status_label.setText("RAG reindex task queued.")
        QTimer.singleShot(3000, self._clear_status_label)

    def _clear_status_label(self):
        """Safely clear the status label."""
        try:
            if self.status_label:
                self.status_label.setText("")
        except RuntimeError:
            pass
