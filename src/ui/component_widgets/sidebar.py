"""Reusable compact widgets rendered in the main-window sidebar."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from .tags import create_tag_chip


class SidebarTaskCompactWidget(QWidget):
    """Compact task row for the sidebar accordion: title plus tags."""

    completion_toggled = pyqtSignal(int, bool)
    ROW_HEIGHT = 56

    def __init__(self, title, tags, task_id=None, is_completed=False, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        top_row = QWidget()
        top_row.setMinimumHeight(22)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)
        self.complete_check = QCheckBox()
        self.complete_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.complete_check.setChecked(bool(is_completed))
        self.complete_check.setStyleSheet("""QCheckBox { spacing: 0px; padding: 0px; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 2px solid #7f8c8d; border-radius: 5px; background-color: rgba(255, 255, 255, 0.06); }
            QCheckBox::indicator:hover { border-color: #b0bec5; background-color: rgba(176, 190, 197, 0.18); }
            QCheckBox::indicator:checked { border-color: #66bb6a; background-color: #2e7d32; image: none; }
            QCheckBox::indicator:checked:hover { border-color: #81c784; background-color: #388e3c; }""")
        self.complete_check.toggled.connect(self._on_toggle_completed)
        top_layout.addWidget(self.complete_check, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.title_label = QLabel((title or "").strip() or "Untitled task")
        self.title_label.setWordWrap(False)
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        top_layout.addWidget(self.title_label, 1)
        layout.addWidget(top_row)
        tags_row = QWidget()
        tags_row.setMinimumHeight(16)
        tags_layout = QHBoxLayout(tags_row)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(4)
        self.tag_chips = []
        if tags:
            for tag in tags:
                chip = create_tag_chip(tag, width=None, height=16, font_size=9, parent=self)
                self.tag_chips.append(chip)
                tags_layout.addWidget(chip)
        else:
            no_tags = QLabel("No tags")
            no_tags.setStyleSheet("font-size: 10px; color: #8a8a8a;")
            self.tag_chips.append(no_tags)
            tags_layout.addWidget(no_tags)
        tags_layout.addStretch()
        layout.addWidget(tags_row)
        self.setFixedHeight(self.ROW_HEIGHT)

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(self.ROW_HEIGHT)
        return hint

    def _on_toggle_completed(self, checked):
        if isinstance(self.task_id, int):
            self.completion_toggled.emit(self.task_id, bool(checked))


class SidebarChatSessionWidget(QWidget):
    """Compact chat-session row with an inline history-tab action."""

    expand_requested = pyqtSignal(int)
    ROW_HEIGHT = 52

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session or {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        text_column = QWidget(self)
        text_layout = QVBoxLayout(text_column)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        title = (self.session.get("name") or "").strip() or "New Chat"
        created_at = str(self.session.get("created_at") or "").strip()
        self.title_label = QLabel(title, text_column)
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.title_label.setWordWrap(False)
        self.title_label.setToolTip(title)
        text_layout.addWidget(self.title_label)
        self.meta_label = QLabel(created_at[:16], text_column)
        self.meta_label.setStyleSheet("font-size: 11px; color: #78909C;")
        text_layout.addWidget(self.meta_label)
        layout.addWidget(text_column, 1)
        self.expand_btn = QToolButton(self)
        self.expand_btn.setText("⤢")
        self.expand_btn.setToolTip("Open the full Chat History tab")
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.setAutoRaise(True)
        self.expand_btn.setFixedSize(24, 24)
        self.expand_btn.setStyleSheet("""QToolButton { border: none; border-radius: 8px; padding: 2px; background-color: transparent; color: #607D8B; font-size: 14px; }
            QToolButton:hover { background-color: rgba(84, 110, 122, 0.16); }""")
        self.expand_btn.clicked.connect(self._emit_expand_requested)
        layout.addWidget(self.expand_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setFixedHeight(self.ROW_HEIGHT)

    def _emit_expand_requested(self):
        session_id = self.session.get("id")
        if isinstance(session_id, int):
            self.expand_requested.emit(session_id)
