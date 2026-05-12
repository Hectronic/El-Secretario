# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox, QLineEdit, QListWidget, QMainWindow, QTabWidget, QWidget

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.ui.main_window import sidebar_content as sidebar_content_module
from src.ui.main_window.sidebar_content import SidebarContentCoordinator


class _Signal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class _Timer:
    def __init__(self):
        self.calls = []

    def start(self, delay_ms):
        self.calls.append(delay_ms)


class _RecordWidget(QWidget):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.favorite_toggled = _Signal()
        self.delete_requested = _Signal()

    def sizeHint(self):
        return super().sizeHint()


class _SummaryWidget(QWidget):
    def __init__(self, data):
        super().__init__()
        self.data = data

    def sizeHint(self):
        return super().sizeHint()


class _SessionWidget(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.expand_requested = _Signal()

    def sizeHint(self):
        return super().sizeHint()


class _Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.history_list = QListWidget()
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.addItem("All")
        self.fav_filter_cb = QCheckBox()
        self.search_input = QLineEdit()
        self.collections_list = QListWidget()
        self.notebooks_list = QListWidget()
        self.sessions_list = QListWidget()
        self.central_tabs = QTabWidget()
        self.current_week_monday = None
        self.current_date_filter = None
        self._pending_history_reload = False
        self._pending_tag_reload = False
        self._sidebar_refresh_timer = _Timer()
        self.db = MagicMock()
        self.notebook_db = MagicMock()
        self.welcome_widget = MagicMock()
        self.open_chat_history_tab = MagicMock()
        self.open_collection_tab = MagicMock()
        self.open_chat_tab = MagicMock()
        self._close_recording_tabs = MagicMock()
        self.refresh_tasks_sidebar = MagicMock()
        self.refresh_tag_filter = MagicMock()
        self.load_collections = MagicMock()
        self.filter_history_list = MagicMock()
        self.load_history_calls = 0
        self.load_favorites_calls = 0
        self.load_today_calls = 0

    def load_history(self, *args, **kwargs):
        self.load_history_calls += 1

    def on_favorite_toggled(self, *args, **kwargs):
        pass

    def delete_recording(self, *args, **kwargs):
        pass


class TestSidebarContentCoordinator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.window = _Window()
        self.coordinator = SidebarContentCoordinator(self.window)
        self.record_patch = patch.object(sidebar_content_module, "RecordingListItemWidget", _RecordWidget)
        self.summary_patch = patch.object(sidebar_content_module, "SummaryListItemWidget", _SummaryWidget)
        self.session_patch = patch.object(sidebar_content_module, "SidebarChatSessionWidget", _SessionWidget)
        self.record_patch.start()
        self.summary_patch.start()
        self.session_patch.start()

        self.window.db.fetch_all.return_value = [
            {"id": 1, "title": "Alpha", "created_at": "2026-05-05 10:00:00", "type": "recording", "tags": "work"}
        ]
        self.window.db.fetch_daily_summaries.return_value = [
            {"date": "2026-05-04", "summary": "Daily summary"}
        ]
        self.window.db.fetch_weekly_summaries.return_value = [
            {"week_start": "2026-05-03", "summary": "Weekly summary"}
        ]
        self.window.db.get_all_tags.return_value = ["work", "home"]
        self.window.db.fetch_by_date_range.return_value = [
            {"id": 10, "tags": "work,home", "created_at": "2026-05-06 12:00:00"}
        ]
        self.window.db.get_weekly_summary.return_value = "Weekly summary"
        self.window.db.fetch_daily_summaries_by_range.return_value = [
            {"date": "2026-05-06", "summary": "Range summary"}
        ]
        self.window.db.get_daily_summary.return_value = "Daily summary"
        self.window.db.fetch_chat_sessions.return_value = [{"id": 99, "name": "Session A"}]
        self.window.notebook_db.get_notebooks.return_value = [{"id": 7, "name": "Notebook"}]

    def tearDown(self):
        self.session_patch.stop()
        self.summary_patch.stop()
        self.record_patch.stop()
        self.window.close()

    def test_load_history_populates_items_and_refreshes_welcome(self):
        self.coordinator.load_history()

        self.assertEqual(self.window.history_list.count(), 3)
        first = self.window.history_list.item(0).data(Qt.ItemDataRole.UserRole)
        self.assertEqual(first["type"], "recording")
        self.window.welcome_widget.load_favorites.assert_called_once()
        self.window.welcome_widget.load_today.assert_called_once()

    def test_request_and_apply_pending_sidebar_reload(self):
        self.coordinator.request_sidebar_reload(include_tags=True, include_history=False, delay_ms=42)
        self.assertTrue(self.window._pending_tag_reload)
        self.assertFalse(self.window._pending_history_reload)
        self.assertEqual(self.window._sidebar_refresh_timer.calls, [42])

        self.coordinator._apply_pending_sidebar_reload()

        self.window.refresh_tag_filter.assert_called_once()
        self.assertEqual(self.window.load_history_calls, 1)
        self.window.refresh_tasks_sidebar.assert_called_once()
        self.assertFalse(self.window._pending_tag_reload)
        self.assertFalse(self.window._pending_history_reload)

    def test_refresh_tag_filter_updates_combo_and_loads_collections(self):
        self.window.current_date_filter = QDate.fromString("2026-05-06", "yyyy-MM-dd")
        self.window.tag_filter_combo.setCurrentText("All")

        self.coordinator.refresh_tag_filter()

        self.assertEqual(self.window.tag_filter_combo.itemText(0), "All")
        self.assertIn("home", [self.window.tag_filter_combo.itemText(i) for i in range(self.window.tag_filter_combo.count())])
        self.window.load_collections.assert_called_once()

    def test_load_chat_sessions_and_notebooks(self):
        self.coordinator.load_chat_sessions()
        self.coordinator.load_notebooks()

        self.assertEqual(self.window.sessions_list.count(), 1)
        self.assertEqual(self.window.notebooks_list.count(), 1)


if __name__ == "__main__":
    unittest.main()
