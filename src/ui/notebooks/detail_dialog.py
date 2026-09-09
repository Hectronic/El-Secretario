"""Notebook-entry detail editor dialog."""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTextEdit, QVBoxLayout


class NoteDetailDialog(QDialog):
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.setWindowTitle(entry["title"] or "Note Details")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(entry["content"])
        self.text_edit.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.text_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def get_content(self): return self.text_edit.toPlainText()
