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

import os
import sys
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.main_window import MainWindow
from src.ui.welcome_widget import WelcomeWidget


class _FakeDB:
    def fetch_favorites(self, limit=5, offset=0):
        return []

    def fetch_by_date_range(self, start_date, end_date, tags=None, favorites_only=False):
        return []


class TestWelcomeDailySummaryButton(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_welcome_button_emits_signal(self):
        widget = WelcomeWidget(_FakeDB())
        try:
            calls = []
            widget.generate_daily_summary_requested.connect(lambda: calls.append(True))

            widget.generate_daily_summary_btn.click()

            self.assertEqual(len(calls), 1)
        finally:
            widget.deleteLater()


class TestMainWindowDailySummaryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.rag_patcher = patch("src.rag_engine.RAGEngine")
        self.rag_patcher.start()

        self.db_patcher = patch("src.ui.main_window.DBManager")
        self.mock_db = self.db_patcher.start().return_value
        self.mock_db.fetch_all.return_value = []
        self.mock_db.get_all_tags.return_value = []
        self.mock_db.fetch_chat_sessions.return_value = []
        self.mock_db.fetch_favorites.return_value = []
        self.mock_db.fetch_by_date_range.return_value = []
        self.mock_db.fetch_daily_summaries.return_value = []
        self.mock_db.fetch_weekly_summaries.return_value = []
        self.mock_db.fetch_daily_summaries_by_range.return_value = []
        self.mock_db.get_daily_summary.return_value = None
        self.mock_db.get_weekly_summary.return_value = None

        self.notebook_db_patcher = patch("src.ui.main_window.NotebookDBManager")
        self.mock_notebook_db = self.notebook_db_patcher.start().return_value
        self.mock_notebook_db.get_notebooks.return_value = []

        self.recorder_patcher = patch("src.ui.main_window.Recorder")
        self.mock_recorder = self.recorder_patcher.start().return_value
        self.mock_recorder.is_recording = False

        self.window = MainWindow()

    def tearDown(self):
        self.window.close()
        self.rag_patcher.stop()
        self.db_patcher.stop()
        self.notebook_db_patcher.stop()
        self.recorder_patcher.stop()

    def test_welcome_button_enqueues_today_daily_summary(self):
        self.window.summary_task_queue.enqueue_daily_summary = MagicMock()

        self.window.welcome_widget.generate_daily_summary_btn.click()

        self.window.summary_task_queue.enqueue_daily_summary.assert_called_once_with(
            {
                "date": date.today().isoformat(),
                "tags_filter": "",
            }
        )


if __name__ == "__main__":
    unittest.main()
