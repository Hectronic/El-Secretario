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

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QDate, QPoint, Qt
from PyQt6.QtWidgets import QApplication, QListWidget, QListWidgetItem, QComboBox, QMainWindow, QCalendarWidget, QTabWidget, QWidget
from PyQt6.QtCore import QSize

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.ui.main_window import sidebar_actions as actions_module
from src.ui.main_window import history_tags_actions as history_tags_actions_module
from src.ui.main_window import chat_sessions_actions as chat_actions_module
from src.ui.main_window import tasks_sidebar_actions as tasks_actions_module
from src.ui.main_window.sidebar_actions import SidebarActionsCoordinator


class _Signal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class _TaskWidget(QWidget):
    def __init__(self, content, tags, task_id=None, is_completed=False, parent=None):
        super().__init__(parent)
        self.content = content
        self.tags = tags
        self.task_id = task_id
        self.is_completed = is_completed
        self.completion_toggled = _Signal()

    def sizeHint(self):
        return QSize(240, 44)


class _TaskItem:
    def __init__(self, task):
        self._task = task
        self._hidden = False
        self._font = MagicMock()

    def data(self, role):
        return self._task if role == Qt.ItemDataRole.UserRole else None

    def checkState(self):
        return Qt.CheckState.Checked if self._task.get("is_completed") else Qt.CheckState.Unchecked

    def font(self):
        return self._font

    def setFont(self, font):
        self._font = font

    def setForeground(self, _fg):
        pass

    def setHidden(self, hidden):
        self._hidden = hidden


class _Menu:
    next_choice_label = None

    def __init__(self, *_args, chosen=None, **_kwargs):
        self.actions = []
        self.chosen = chosen

    def addAction(self, label):
        action = object()
        self.actions.append((label, action))
        return action

    def exec(self, _point):
        if self.chosen is not None:
            return self.chosen
        if self.next_choice_label is not None:
            for label, action in self.actions:
                if label == self.next_choice_label:
                    return action
        return self.chosen


class _Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tasks_sidebar_list = QListWidget()
        self.sessions_list = QListWidget()
        self.history_list = QListWidget()
        self.collections_list = QListWidget()
        self.central_tabs = QTabWidget()
        self.calendar = QCalendarWidget()
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.addItem("All")
        self.current_week_monday = None
        self.current_date_filter = None
        self.tasks_sidebar_limit = 20
        self._last_highlighted_dates = []
        self.db = MagicMock()
        self.open_recording_tab = MagicMock()
        self.open_chat_tab = MagicMock()
        self.open_floating_chat = MagicMock()
        self.open_recording_editor_tab = MagicMock()
        self.open_note_tab = MagicMock()
        self.open_summary_tab = MagicMock()
        self.open_collection_tab = MagicMock()
        self.open_collection_chat = MagicMock()
        self.load_chat_sessions = MagicMock()
        self.request_sidebar_reload = MagicMock()
        self.update_calendar_visuals = MagicMock()
        self.refresh_tasks_sidebar = MagicMock()
        self.sync_active_tabs = MagicMock()
        self.on_task_sidebar_item_changed = MagicMock()
        self._sync_chat_context_section = MagicMock()
        self._remove_floating_host = MagicMock()
        self._find_floating_chat_host = MagicMock(return_value=None)
        self.sidebar_sync = MagicMock()


class TestSidebarActionsCoordinator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.window = _Window()
        self.coordinator = SidebarActionsCoordinator(self.window)
        self.task_patch = patch.object(tasks_actions_module, "SidebarTaskCompactWidget", _TaskWidget)
        self.task_patch.start()
        self.menu_patch = patch.object(actions_module, "QMenu", _Menu, create=True)
        self.menu_patch.start()
        self.tasks_menu_patch = patch.object(tasks_actions_module, "QMenu", _Menu)
        self.tasks_menu_patch.start()
        self.chat_menu_patch = patch.object(chat_actions_module, "QMenu", _Menu)
        self.chat_menu_patch.start()
        self.history_tags_menu_patch = patch.object(history_tags_actions_module, "QMenu", _Menu)
        self.history_tags_menu_patch.start()
        self.tasks_msgbox_patch = patch.object(tasks_actions_module, "QMessageBox")
        self.mock_tasks_msgbox = self.tasks_msgbox_patch.start()
        self.chat_msgbox_patch = patch.object(chat_actions_module, "QMessageBox")
        self.mock_chat_msgbox = self.chat_msgbox_patch.start()
        self.mock_tasks_msgbox.question.return_value = self.mock_tasks_msgbox.StandardButton.Yes
        self.mock_chat_msgbox.question.return_value = self.mock_chat_msgbox.StandardButton.Yes

        self.window.db.get_recent_incomplete_tasks.return_value = [
            {"id": 1, "content": "Task", "tags": "alpha", "record_id": None, "is_completed": 0}
        ]
        self.window.db.get_tasks_by_date_range.return_value = []
        self.window.db.get_tasks_by_date.return_value = []
        self.window.db.fetch_chat_sessions.return_value = [{"id": 8, "name": "Chat"}]

    def tearDown(self):
        _Menu.next_choice_label = None
        self.chat_msgbox_patch.stop()
        self.tasks_msgbox_patch.stop()
        self.history_tags_menu_patch.stop()
        self.chat_menu_patch.stop()
        self.tasks_menu_patch.stop()
        self.menu_patch.stop()
        self.task_patch.stop()
        self.window.close()

    def test_refresh_tasks_sidebar_populates_task_widget(self):
        self.coordinator.refresh_tasks_sidebar()
        self.assertEqual(self.window.tasks_sidebar_list.count(), 1)

    def test_task_item_changed_toggles_completion(self):
        item = _TaskItem({"id": 3, "is_completed": 0})
        self.coordinator.on_task_sidebar_item_changed(item)
        self.window.db.toggle_task_completion.assert_called_once_with(3, False)

    def test_calendar_navigation_updates_filters(self):
        self.window.calendar.setSelectedDate(QDate(2026, 3, 8))
        self.coordinator.on_calendar_date_changed()
        self.window.request_sidebar_reload.assert_called()
        self.window.sync_active_tabs.assert_called()

    def test_delete_chat_session_by_id_clears_session(self):
        self.coordinator.delete_chat_session_by_id(8)
        self.window.db.delete_chat_session.assert_called_once_with(8)
        self.window.load_chat_sessions.assert_called_once()

    def test_show_chat_sidebar_context_menu_routes_actions(self):
        item = QListWidgetItem("chat")
        item.setData(Qt.ItemDataRole.UserRole, {"id": 8, "name": "Chat"})
        self.window.sessions_list.addItem(item)
        self.window.sessions_list.itemAt = MagicMock(return_value=item)

        _Menu.next_choice_label = "Open"
        self.coordinator.show_chat_sidebar_context_menu(QPoint(0, 0))
        self.window.open_chat_tab.assert_called_once_with(8)

        self.window.open_chat_tab.reset_mock()
        _Menu.next_choice_label = "Open Floating"
        self.coordinator.show_chat_sidebar_context_menu(QPoint(0, 0))
        self.window.open_floating_chat.assert_called_once_with(8)

        self.window.open_floating_chat.reset_mock()
        self.window.db.delete_chat_session.reset_mock()
        _Menu.next_choice_label = "Delete"
        self.coordinator.show_chat_sidebar_context_menu(QPoint(0, 0))
        self.window.db.delete_chat_session.assert_called_once_with(8)

    def test_delete_selected_chat_session_uses_current_item(self):
        item = QListWidgetItem("chat")
        item.setData(Qt.ItemDataRole.UserRole, {"id": 8, "name": "Chat"})
        self.window.sessions_list.addItem(item)
        self.window.sessions_list.setCurrentItem(item)

        self.coordinator.delete_selected_chat_session()
        self.window.db.delete_chat_session.assert_called_once_with(8)

    def test_show_history_item_context_menu_routes_recording_actions(self):
        item = QListWidgetItem("r")
        item.setData(Qt.ItemDataRole.UserRole, {"id": 11, "type": "recording"})
        self.window.history_list.addItem(item)
        self.window.history_list.itemAt = MagicMock(return_value=item)
        _Menu.next_choice_label = "Open"
        self.coordinator.show_history_item_context_menu(QPoint(0, 0))
        self.window.open_recording_tab.assert_called_once_with(11)

        self.window.open_recording_tab.reset_mock()
        _Menu.next_choice_label = "Open Audio Editor Tab"
        self.coordinator.show_history_item_context_menu(QPoint(0, 0))
        self.window.open_recording_editor_tab.assert_called_once_with(11)

    def test_show_history_item_context_menu_routes_note_and_summary(self):
        note = QListWidgetItem("n")
        note.setData(Qt.ItemDataRole.UserRole, {"id": 12, "type": "note"})
        self.window.history_list.addItem(note)
        self.window.history_list.itemAt = MagicMock(return_value=note)
        _Menu.next_choice_label = "Open"
        self.coordinator.show_history_item_context_menu(QPoint(0, 0))
        self.window.open_note_tab.assert_called_once_with(12)

        summary_data = {"type": "daily", "date": "2026-05-11"}
        summary = QListWidgetItem("s")
        summary.setData(Qt.ItemDataRole.UserRole, summary_data)
        self.window.history_list.addItem(summary)
        self.window.history_list.itemAt = MagicMock(return_value=summary)
        _Menu.next_choice_label = "Open"
        self.coordinator.show_history_item_context_menu(QPoint(0, 0))
        self.window.open_summary_tab.assert_called_once_with(summary_data)

    def test_show_tags_sidebar_context_menu_routes_open_and_chat(self):
        item = QListWidgetItem("backend")
        item.setData(Qt.ItemDataRole.UserRole, "backend")
        self.window.collections_list.addItem(item)
        self.window.collections_list.itemAt = MagicMock(return_value=item)

        _Menu.next_choice_label = "Open"
        self.coordinator.show_tags_sidebar_context_menu(QPoint(0, 0))
        self.window.open_collection_tab.assert_called_once_with("backend")

        self.window.open_collection_tab.reset_mock()
        _Menu.next_choice_label = "Chat"
        self.coordinator.show_tags_sidebar_context_menu(QPoint(0, 0))
        self.window.open_collection_chat.assert_called_once_with("backend")


if __name__ == "__main__":
    unittest.main()
