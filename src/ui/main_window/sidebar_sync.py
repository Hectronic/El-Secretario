# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt

from src.ui.calendar_widget import CalendarWidget
from src.ui.chat_widget import ChatWidget
from src.ui.tasks_list_widget import TasksListWidget


class SidebarSyncCoordinator:
    """Apply sidebar selection state to visible tabs and the chat context panel."""

    def __init__(self, window):
        self.window = window

    def current_chat_widget(self):
        widget = self.window.central_tabs.currentWidget() if hasattr(self.window, "central_tabs") else None
        return widget if isinstance(widget, ChatWidget) else None

    def sync_chat_context_section(self, chat_widget=None):
        section = self.window._right_sidebar_sections.get("chat_context")
        if section is None:
            return

        if chat_widget is None:
            chat_widget = self.current_chat_widget()

        container = section.get("container")
        if not isinstance(chat_widget, ChatWidget):
            if container is not None:
                container.setVisible(False)
            if self.window._active_right_section == "chat_context":
                fallback = self.window._right_sidebar_last_non_chat_section
                if fallback not in self.window._right_sidebar_sections:
                    fallback = "tasks" if "tasks" in self.window._right_sidebar_sections else None
                self.window._set_active_right_section(fallback)
            return

        if container is not None:
            container.setVisible(True)
        sidebar_panel = section.get("context_panel")
        if sidebar_panel is not None and hasattr(chat_widget, "context_panel"):
            try:
                sidebar_panel.restore_from_panel(chat_widget.context_panel)
            except Exception:
                logging.exception("Failed to sync active chat context sidebar")
        self.window._set_active_right_section("chat_context")

    def sync_active_tabs(self):
        """Push current sidebar selection and tags to active tabs (Calendar, Chat)."""
        tag = self.window.tag_filter_combo.currentText()
        tags_filter = tag if tag != "All" else None

        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, CalendarWidget):
                widget.set_selection(self.window.current_week_monday, self.window.current_date_filter, tags_filter)
            elif isinstance(widget, ChatWidget):
                widget.update_from_global_selection(
                    self.window.current_week_monday,
                    self.window.current_date_filter,
                    tags_filter or "",
                )
            elif isinstance(widget, TasksListWidget):
                widget.set_global_filters(self.window.current_week_monday, self.window.current_date_filter, tags_filter)

        for host in self.window.floating_chat_hosts:
            widget = host.property("chat_widget")
            if isinstance(widget, ChatWidget):
                widget.update_from_global_selection(
                    self.window.current_week_monday,
                    self.window.current_date_filter,
                    tags_filter or "",
                )
