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

from src.ui.main_window.calendar_sidebar_actions import CalendarSidebarActionsCoordinator
from src.ui.main_window.chat_sessions_actions import ChatSessionsActionsCoordinator
from src.ui.main_window.history_tags_actions import HistoryTagsActionsCoordinator
from src.ui.main_window.tasks_sidebar_actions import TasksSidebarActionsCoordinator


class SidebarActionsCoordinator:
    def __init__(self, window):
        self.window = window
        self.tasks_sidebar_actions = TasksSidebarActionsCoordinator(window)
        self.chat_sessions_actions = ChatSessionsActionsCoordinator(window)
        self.calendar_sidebar_actions = CalendarSidebarActionsCoordinator(window)
        self.history_tags_actions = HistoryTagsActionsCoordinator(window)

    def refresh_tasks_sidebar(self):
        self.tasks_sidebar_actions.refresh_tasks_sidebar()

    def _toggle_sidebar_task_completion(self, task_id, is_completed):
        self.tasks_sidebar_actions._toggle_sidebar_task_completion(task_id, is_completed)

    def on_task_sidebar_item_changed(self, item):
        self.tasks_sidebar_actions.on_task_sidebar_item_changed(item)

    def show_tasks_sidebar_context_menu(self, point):
        self.tasks_sidebar_actions.show_tasks_sidebar_context_menu(point)

    def on_chat_session_clicked(self, item):
        self.chat_sessions_actions.on_chat_session_clicked(item)

    def show_chat_sidebar_context_menu(self, point):
        self.chat_sessions_actions.show_chat_sidebar_context_menu(point)

    def show_history_item_context_menu(self, point):
        self.history_tags_actions.show_history_item_context_menu(point)

    def show_tags_sidebar_context_menu(self, point):
        self.history_tags_actions.show_tags_sidebar_context_menu(point)

    def delete_chat_session_by_id(self, session_id):
        self.chat_sessions_actions.delete_chat_session_by_id(session_id)

    def delete_selected_chat_session(self):
        self.chat_sessions_actions.delete_selected_chat_session()

    def on_calendar_date_changed(self):
        self.calendar_sidebar_actions.on_calendar_date_changed()

    def sync_active_tabs(self):
        self.calendar_sidebar_actions.sync_active_tabs()

    def prev_week_sidebar(self):
        self.calendar_sidebar_actions.prev_week_sidebar()

    def next_week_sidebar(self):
        self.calendar_sidebar_actions.next_week_sidebar()

    def update_calendar_visuals(self):
        self.calendar_sidebar_actions.update_calendar_visuals()

    def reset_date_filter(self):
        self.calendar_sidebar_actions.reset_date_filter()
