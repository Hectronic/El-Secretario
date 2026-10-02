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
from src.ui.timeline.widget import TimelineWidget


class SidebarSyncCoordinator:
    """Apply sidebar selection state to visible tabs and the chat context panel."""

    def __init__(self, window):
        self.window = window
        self._context_panel = None
        self._chat_context_slot = None

    def bind_chat_context_panel(self, panel):
        """Connect the right-sidebar editor to the currently selected chat."""
        self._context_panel = panel
        panel.context_changed.connect(self.apply_sidebar_context_to_chat)
        panel.add_context_requested.connect(self.add_context_to_active_chat)
        panel.remove_context_requested.connect(self.remove_context_from_active_chat)
        panel.reset_extra_context_requested.connect(self.reset_active_chat_context)
        panel.clear_chat_requested.connect(self.clear_active_chat_history)

    def current_chat_widget(self):
        widget = self.window.central_tabs.currentWidget() if hasattr(self.window, "central_tabs") else None
        return widget if isinstance(widget, ChatWidget) else None

    def sync_chat_context_section(self, chat_widget=None):
        section = self.window._right_sidebar_sections.get("chat_context")
        if section is None:
            return

        if chat_widget is None:
            chat_widget = self.current_chat_widget()
        elif chat_widget is not self.current_chat_widget():
            return

        container = section.get("container")
        if not isinstance(chat_widget, ChatWidget):
            if container is not None:
                container.setVisible(False)
            sidebar_panel = section.get("context_panel")
            set_interactive = getattr(sidebar_panel, "set_interactive", None)
            if callable(set_interactive):
                set_interactive(False)
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
                set_interactive = getattr(sidebar_panel, "set_interactive", None)
                if callable(set_interactive):
                    set_interactive(True)
            except Exception:
                logging.exception("Failed to sync active chat context sidebar")
        self.window._set_active_right_section("chat_context")

    def apply_sidebar_context_to_chat(self):
        if self.window._active_right_section != "chat_context":
            return
        chat_widget = self.current_chat_widget()
        if chat_widget is None or self._context_panel is None:
            return
        chat_widget.apply_context_state(self._context_panel.serialize_state())

    def add_context_to_active_chat(self):
        chat_widget = self.current_chat_widget()
        if chat_widget is not None:
            chat_widget.add_context()

    def reset_active_chat_context(self):
        chat_widget = self.current_chat_widget()
        if chat_widget is not None:
            chat_widget.reset_extra_context()

    def remove_context_from_active_chat(self):
        chat_widget = self.current_chat_widget()
        if chat_widget is not None:
            chat_widget.show_remove_context_menu()

    def clear_active_chat_history(self):
        chat_widget = self.current_chat_widget()
        if chat_widget is not None:
            chat_widget.clear_history()

    def activate_chat_context_sidebar(self, chat_widget):
        """Open the sidebar editor for a tabbed chat's compact-summary action."""
        if self.window.central_tabs is None:
            return
        index = next(
            (i for i in range(self.window.central_tabs.count())
             if self.window.central_tabs.widget(i) is chat_widget),
            -1,
        )
        if index < 0:
            return
        self.window.central_tabs.setCurrentIndex(index)
        self.sync_chat_context_section(chat_widget)
        panel = self._context_panel
        if panel is not None:
            focus_target = getattr(panel, "add_context_btn", panel)
            focus_target.setFocus(Qt.FocusReason.OtherFocusReason)

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
            elif isinstance(widget, TimelineWidget):
                widget.set_global_filters(self.window.current_week_monday, self.window.current_date_filter, tags_filter)

        for host in self.window.floating_chat_hosts:
            widget = host.property("chat_widget")
            if isinstance(widget, ChatWidget):
                widget.update_from_global_selection(
                    self.window.current_week_monday,
                    self.window.current_date_filter,
                    tags_filter or "",
                )
