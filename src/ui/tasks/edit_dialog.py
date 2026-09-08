"""Task editing dialog owned by the task-board feature."""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)

from src.ui.components import TagsLineEdit


class TaskEditDialog(QDialog):
    """Modal editor shared by task-board and sidebar task actions."""

    def __init__(self, db, parent=None, title="Task", task_data=None):
        super().__init__(parent)
        self.db = db
        self.task_data = task_data or {}
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(560, 360)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Task content"))
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Describe the task...")
        self.content_input.setMinimumHeight(110)
        self.content_input.setPlainText((self.task_data.get("content") or "").strip())
        layout.addWidget(self.content_input)

        layout.addWidget(QLabel("Notes (optional)"))
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Extra context, links, blockers...")
        self.notes_input.setMinimumHeight(90)
        self.notes_input.setPlainText((self.task_data.get("notes") or "").strip())
        layout.addWidget(self.notes_input)

        layout.addWidget(QLabel("Tags"))
        self.tags_input = TagsLineEdit()
        self.tags_input.set_tags(self.db.get_all_tags() if hasattr(self.db, "get_all_tags") else [])
        initial_tags = (self.task_data.get("tags") or "").strip()
        if not initial_tags and isinstance(self.task_data.get("record_id"), int):
            initial_tags = (self.task_data.get("record_tags") or "").strip()
        self.tags_input.setText(initial_tags)
        layout.addWidget(self.tags_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #f44336; font-size: 12px;")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if not self.get_content():
            self.error_label.setText("Task content is required.")
            self.content_input.setFocus()
            return
        self.accept()

    def get_content(self):
        return self.content_input.toPlainText().strip()

    def get_notes(self):
        notes = self.notes_input.toPlainText().strip()
        return notes or None

    def get_tags(self):
        tags = self.tags_input.text().strip()
        return tags or None
