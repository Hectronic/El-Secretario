from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class NoteEntryWidget(QWidget):
    """Visual representation of one notebook entry."""

    delete_requested = pyqtSignal()

    def __init__(self, entry, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        header = QHBoxLayout()
        title_text = entry["title"] or entry["created_at"]
        type_icon = "🎤" if entry["type"] == "audio" else "📝"
        header.addWidget(QLabel(f"{type_icon} <b>{title_text}</b>"))
        header.addStretch()
        if entry["type"] == "audio":
            duration = entry.get("duration", 0) or 0
            header.addWidget(QLabel(f"{int(duration // 60)}m {int(duration % 60)}s"))

        delete_button = QPushButton("🗑")
        delete_button.setFixedSize(30, 30)
        delete_button.setStyleSheet(
            "QPushButton { background-color: transparent; color: #f44336; border: none; "
            "font-size: 16px; } QPushButton:hover { background-color: #333; border-radius: 15px; }"
        )
        delete_button.clicked.connect(self.delete_requested)
        header.addWidget(delete_button)
        layout.addLayout(header)

        content = QLabel(entry["content"])
        content.setWordWrap(True)
        content.setStyleSheet("color: #ccc; margin-top: 5px;")
        layout.addWidget(content)
