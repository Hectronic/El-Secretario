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
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QCloseEvent

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.main_window import MainWindow


class DummyCleanupWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.cleanup_calls = 0

    def cleanup(self):
        self.cleanup_calls += 1


class DummyWorker:
    def __init__(self):
        self.request_interruption_calls = 0
        self.quit_calls = 0
        self.wait_calls = 0
        self.cancel_calls = 0
        self.running = True

    def isRunning(self):
        return self.running

    def requestInterruption(self):
        self.request_interruption_calls += 1

    def quit(self):
        self.quit_calls += 1
        self.running = False

    def wait(self, _timeout=None):
        self.wait_calls += 1
        return True

    def cancel(self):
        self.cancel_calls += 1


class TestShutdownCleanupStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.db_patcher = patch("src.ui.main_window.DBManager")
        self.nb_db_patcher = patch("src.ui.main_window.NotebookDBManager")
        self.recorder_patcher = patch("src.ui.main_window.Recorder")
        self.theme_patcher = patch("src.ui.main_window.apply_theme")

        self.mock_db = self.db_patcher.start().return_value
        self.mock_nb_db = self.nb_db_patcher.start().return_value
        self.mock_recorder = self.recorder_patcher.start().return_value
        self.theme_patcher.start()

        self.window = MainWindow()
        self.window.central_tabs.clear()

    def tearDown(self):
        self.window.close()
        self.db_patcher.stop()
        self.nb_db_patcher.stop()
        self.recorder_patcher.stop()
        self.theme_patcher.stop()

    def test_close_tab_calls_cleanup(self):
        w = DummyCleanupWidget()
        idx = self.window.central_tabs.addTab(w, "cleanup")
        self.window.close_tab(idx)
        self.assertEqual(w.cleanup_calls, 1)

    def test_close_event_cleans_many_tabs_and_workers(self):
        widgets = []
        for i in range(100):
            w = DummyCleanupWidget()
            widgets.append(w)
            self.window.central_tabs.addTab(w, f"tab-{i}")

        self.window.search_thread = DummyWorker()
        self.window.regen_worker = DummyWorker()
        self.window.recorder = MagicMock()
        self.window.recorder.is_recording = True

        self.window.closeEvent(QCloseEvent())

        for w in widgets:
            self.assertEqual(w.cleanup_calls, 1)

        self.assertEqual(self.window.search_thread, None)
        self.assertEqual(self.window.regen_worker, None)
        self.window.recorder.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
