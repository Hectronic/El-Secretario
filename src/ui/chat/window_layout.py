"""Visual composition for the legacy standalone chat window."""

from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


def build_chat_window_layout(window):
    """Build the standalone chat controls and connect local UI actions."""
    layout = QVBoxLayout(window)
    top_layout = QHBoxLayout()
    top_layout.addWidget(QLabel("Collection:"))
    window.collection_combo = QComboBox()
    window.collection_combo.addItem("All")
    top_layout.addWidget(window.collection_combo)
    top_layout.addStretch()
    layout.addLayout(top_layout)

    window.display = QTextEdit()
    window.display.setReadOnly(True)
    window.display.setPlaceholderText("Ask anything about your notes...")
    layout.addWidget(window.display)

    input_layout = QHBoxLayout()
    window.input_field = QLineEdit()
    window.input_field.setPlaceholderText("Type your question here...")
    window.input_field.returnPressed.connect(window.send_message)
    input_layout.addWidget(window.input_field)
    window.send_btn = QPushButton("Send")
    window.send_btn.clicked.connect(window.send_message)
    input_layout.addWidget(window.send_btn)
    layout.addLayout(input_layout)

    window.setStyleSheet(
        """
        ChatWindow { border: 3px solid #2196F3; }
        QTextEdit { border: 1px solid #ccc; border-radius: 3px; padding: 5px; }
        """
    )
