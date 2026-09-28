"""Saved chat-session sidebar rendering."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from src.ui.chat_history_widget import ChatHistoryWidget
from src.ui.component_widgets.sidebar import SidebarChatSessionWidget
from src.ui.chat.workflows import filter_chat_sessions


class SidebarSessionsCoordinator:
    """Render saved sessions and synchronize open history tabs."""

    def __init__(self, window):
        self.window = window

    def load_chat_sessions(self):
        self.window.sessions_list.clear()
        search = getattr(self.window, "chat_session_search", None)
        query = search.text() if search is not None else ""
        sessions = filter_chat_sessions(self.window.db.fetch_chat_sessions(), query)
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
        feedback = getattr(self.window, "chat_session_search_feedback", None)
        if feedback is not None:
            feedback.setText(
                "No hay conversaciones guardadas." if not sessions and not query.strip()
                else ("No hay conversaciones que coincidan." if not sessions else f"{len(sessions)} conversaciones")
            )
