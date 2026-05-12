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
from PyQt6.QtWidgets import QMenu


class HistoryTagsActionsCoordinator:
    """Own history and tags sidebar context-menu actions."""

    def __init__(self, window):
        self.window = window

    def show_history_item_context_menu(self, point):
        item = self.window.history_list.itemAt(point)
        if item is None:
            return

        data = item.data(Qt.ItemDataRole.UserRole) or {}
        item_type = data.get("type", "recording")
        menu = QMenu(self.window)

        if item_type == "recording":
            open_action = menu.addAction("Open")
            open_new_action = menu.addAction("Open Audio Editor Tab")
            chosen = menu.exec(self.window.history_list.viewport().mapToGlobal(point))
            if chosen == open_action:
                self.window.open_recording_tab(data["id"])
            elif chosen == open_new_action:
                self.window.open_recording_editor_tab(data["id"])
            return

        if item_type == "note":
            open_action = menu.addAction("Open")
            chosen = menu.exec(self.window.history_list.viewport().mapToGlobal(point))
            if chosen == open_action:
                self.window.open_note_tab(data["id"])
            return

        open_action = menu.addAction("Open")
        chosen = menu.exec(self.window.history_list.viewport().mapToGlobal(point))
        if chosen == open_action:
            self.window.open_summary_tab(data)

    def show_tags_sidebar_context_menu(self, point):
        item = self.window.collections_list.itemAt(point)
        if not item:
            return

        tag = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if not tag or tag == "No tags.":
            return

        menu = QMenu(self.window)
        open_action = menu.addAction("Open")
        chat_action = menu.addAction("Chat")

        chosen = menu.exec(self.window.collections_list.viewport().mapToGlobal(point))
        if chosen == open_action:
            self.window.open_collection_tab(tag)
        elif chosen == chat_action:
            self.window.open_collection_chat(tag)
