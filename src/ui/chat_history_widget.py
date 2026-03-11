from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QMenu, QVBoxLayout, QWidget


class ChatHistoryWidget(QWidget):
    session_requested = pyqtSignal(int)
    session_delete_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("💬 Chat History")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #607D8B;")
        layout.addWidget(title)

        self.sessions_list = QListWidget()
        self.sessions_list.setProperty("class", "embedded-list")
        self.sessions_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sessions_list.itemClicked.connect(self._on_item_clicked)
        self.sessions_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sessions_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.sessions_list)

    def set_sessions(self, sessions):
        self.sessions_list.clear()
        for session in sessions:
            item = QListWidgetItem(f"{session['name']} ({session['created_at'][:16]})")
            item.setData(Qt.ItemDataRole.UserRole, session)
            self.sessions_list.addItem(item)

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
