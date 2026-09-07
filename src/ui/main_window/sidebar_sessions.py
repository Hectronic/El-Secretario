"""Saved chat-session sidebar rendering."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from src.ui.chat_history_widget import ChatHistoryWidget
from src.ui.components import SidebarChatSessionWidget


class SidebarSessionsCoordinator:
    """Render saved sessions and synchronize open history tabs."""

    def __init__(self, window):
        self.window = window

    def load_chat_sessions(self):
        self.window.sessions_list.clear()
        sessions = self.window.db.fetch_chat_sessions()
        for session in sessions:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, session)
            self.window.sessions_list.addItem(item)
            widget = SidebarChatSessionWidget(session, parent=self.window.sessions_list)
            widget.expand_requested.connect(lambda _session_id=None: self.window.open_chat_history_tab())
            item.setSizeHint(widget.sizeHint())
            self.window.sessions_list.setItemWidget(item, widget)
        for index in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(index)
            if isinstance(widget, ChatHistoryWidget):
                widget.set_sessions(sessions)
