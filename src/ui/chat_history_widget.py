import json

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class ChatHistorySessionCard(QWidget):
    open_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)

    def __init__(self, session: dict, parent=None):
        super().__init__(parent)
        self.session = session or {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        title = (self.session.get("name") or "").strip() or "New Chat"
        created_at = str(self.session.get("created_at") or "").strip()[:16]

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)

        self.title_label = QLabel(title, self)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.title_label.setToolTip(title)
        title_col.addWidget(self.title_label)

        self.meta_label = QLabel(created_at or "No date", self)
        self.meta_label.setStyleSheet("font-size: 11px; color: #78909C;")
        title_col.addWidget(self.meta_label)
        top_row.addLayout(title_col, 1)

        self.open_btn = QPushButton("Open", self)
        self.open_btn.setProperty("class", "calendar-primary-btn")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.setMinimumHeight(28)
        self.open_btn.clicked.connect(self._emit_open_requested)
        top_row.addWidget(self.open_btn)

        self.delete_btn = QToolButton(self)
        self.delete_btn.setText("🗑")
        self.delete_btn.setToolTip("Delete chat session")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setAutoRaise(True)
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setStyleSheet("""
            QToolButton {
                border: 1px solid rgba(244, 67, 54, 0.35);
                border-radius: 8px;
                color: #de6a6a;
                background-color: transparent;
                font-size: 14px;
            }
            QToolButton:hover {
                background-color: rgba(244, 67, 54, 0.12);
            }
        """)
        self.delete_btn.clicked.connect(self._emit_delete_requested)
        top_row.addWidget(self.delete_btn)

        layout.addLayout(top_row)

        self.preview_label = QLabel(self._build_preview_text(), self)
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("font-size: 12px; color: #90A4AE;")
        self.preview_label.setMaximumHeight(40)
        layout.addWidget(self.preview_label)

        self.setFixedHeight(92)

    def _build_preview_text(self):
        messages_raw = self.session.get("messages")
        try:
            messages = json.loads(messages_raw) if messages_raw else []
        except Exception:
            messages = []

        for message in messages:
            content = str((message or {}).get("content") or "").strip()
            if content:
                return content[:140] + ("..." if len(content) > 140 else "")
        return "No messages yet."

    def _emit_open_requested(self):
        session_id = self.session.get("id")
        if isinstance(session_id, int):
            self.open_requested.emit(session_id)

    def _emit_delete_requested(self):
        session_id = self.session.get("id")
        if isinstance(session_id, int):
            self.delete_requested.emit(session_id)


class ChatHistoryWidget(QWidget):
    session_requested = pyqtSignal(int)
    session_delete_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_sessions = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title = QLabel("Chat History")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #607D8B;")
        title_row.addWidget(title)

        title_row.addStretch()

        self.count_label = QLabel("0 sessions")
        self.count_label.setStyleSheet("font-size: 12px; color: #78909C;")
        title_row.addWidget(self.count_label)
        layout.addLayout(title_row)

        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(8)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search chats by title or message...")
        self.search_input.textChanged.connect(self._apply_filters)
        controls_row.addWidget(self.search_input, 1)

        self.clear_search_btn = QPushButton("Clear", self)
        self.clear_search_btn.setProperty("class", "calendar-nav-btn")
        self.clear_search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_search_btn.setMinimumHeight(34)
        self.clear_search_btn.clicked.connect(self.search_input.clear)
        controls_row.addWidget(self.clear_search_btn)
        layout.addLayout(controls_row)

        self.summary_label = QLabel("Browse, search, and reopen previous chat sessions.")
        self.summary_label.setStyleSheet("font-size: 12px; color: #90A4AE;")
        layout.addWidget(self.summary_label)

        self.sessions_list = QListWidget()
        self.sessions_list.setProperty("class", "embedded-list")
        self.sessions_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sessions_list.itemClicked.connect(self._on_item_clicked)
        self.sessions_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sessions_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.sessions_list, 1)

        self.empty_label = QLabel("No chat sessions found.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("font-size: 13px; color: #78909C; padding: 16px;")
        layout.addWidget(self.empty_label)
        self.empty_label.hide()

    def set_sessions(self, sessions):
        self._all_sessions = list(sessions or [])
        self._apply_filters()

    def _apply_filters(self):
        query = self.search_input.text().strip().lower()
        if query:
            filtered = [s for s in self._all_sessions if self._session_matches(s, query)]
        else:
            filtered = list(self._all_sessions)
        self._render_sessions(filtered)

    def _render_sessions(self, sessions):
        self.sessions_list.clear()
        self.count_label.setText(f"{len(sessions)} sessions")
        self.empty_label.setVisible(len(sessions) == 0)
        self.sessions_list.setVisible(len(sessions) > 0)

        for session in sessions:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, session)
            card = ChatHistorySessionCard(session, parent=self.sessions_list)
            card.open_requested.connect(self.session_requested.emit)
            card.delete_requested.connect(self.session_delete_requested.emit)
            item.setSizeHint(card.sizeHint())
            self.sessions_list.addItem(item)
            self.sessions_list.setItemWidget(item, card)

    def _session_matches(self, session, query):
        name = str(session.get("name") or "").lower()
        created_at = str(session.get("created_at") or "").lower()
        messages = str(session.get("messages") or "").lower()
        return query in name or query in created_at or query in messages

    def _on_item_clicked(self, item):
        session = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(session, dict) and isinstance(session.get("id"), int):
            self.session_requested.emit(session["id"])

    def _show_context_menu(self, point):
        item = self.sessions_list.itemAt(point)
        if not item:
            return

        session = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(session, dict) or not isinstance(session.get("id"), int):
            return

        menu = QMenu(self)
        open_action = menu.addAction("Open")
        delete_action = menu.addAction("Delete")

        chosen = menu.exec(self.sessions_list.viewport().mapToGlobal(point))
        if chosen == open_action:
            self.session_requested.emit(session["id"])
        elif chosen == delete_action:
            self.session_delete_requested.emit(session["id"])
