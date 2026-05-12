# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu, QMessageBox


class ChatSessionsActionsCoordinator:
    """Own chat sessions sidebar actions and deletion flow."""

    def __init__(self, window):
        self.window = window

    def on_chat_session_clicked(self, item):
        session = item.data(Qt.ItemDataRole.UserRole)
        self.window.open_chat_tab(session["id"])

    def show_chat_sidebar_context_menu(self, point):
        item = self.window.sessions_list.itemAt(point)
        if not item:
            return

        session = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(session, dict):
            return

        menu = QMenu(self.window)
        open_action = menu.addAction("Open")
        open_floating_action = menu.addAction("Open Floating")
        delete_action = menu.addAction("Delete")

        chosen = menu.exec(self.window.sessions_list.viewport().mapToGlobal(point))
        if chosen == open_action:
            self.window.open_chat_tab(session["id"])
        elif chosen == open_floating_action:
            self.window.open_floating_chat(session["id"])
        elif chosen == delete_action:
            self.delete_chat_session_by_id(session["id"])

    def delete_chat_session_by_id(self, session_id):
        sessions = self.window.db.fetch_chat_sessions()
        session = next((s for s in sessions if s.get("id") == session_id), None)
        if not session:
            return

        reply = QMessageBox.question(
            self.window,
            "Delete Chat",
            f"Are you sure you want to delete '{session['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.window.db.delete_chat_session(session["id"])
        self.window.load_chat_sessions()

        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if widget and getattr(widget, "current_session_id", None) == session["id"]:
                self.window.central_tabs.removeTab(i)
                widget.deleteLater()
                break
        floating_host = self.window._find_floating_chat_host(session["id"])
        if floating_host is not None:
            widget = floating_host.property("chat_widget")
            if widget is not None:
                widget.setParent(None)
            self.window._remove_floating_host(floating_host)
            if widget is not None:
                widget.deleteLater()
        self.window._sync_chat_context_section()

    def delete_selected_chat_session(self):
        item = self.window.sessions_list.currentItem()
        if not item:
            return
        session = item.data(Qt.ItemDataRole.UserRole)
        self.delete_chat_session_by_id(session["id"])
