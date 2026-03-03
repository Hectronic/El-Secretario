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
import tempfile
import shutil
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.main_window import MainWindow
from src.ui.welcome_widget import WelcomeWidget
from src.ui.dialogs import SettingsWidget
from src.ui.components import SidebarTaskCompactWidget, create_tag_chip


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
        cls._qsettings_dir = tempfile.mkdtemp(prefix="secretario_qsettings_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            cls._qsettings_dir,
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_qsettings_dir") and os.path.isdir(cls._qsettings_dir):
            shutil.rmtree(cls._qsettings_dir, ignore_errors=True)

    def test_welcome_button_emits_signal(self):
        widget = WelcomeWidget(_FakeDB())
        try:
            calls = []
            widget.generate_daily_summary_requested.connect(lambda: calls.append(True))

            widget.generate_daily_summary_btn.click()

            self.assertEqual(len(calls), 1)
        finally:
            widget.deleteLater()

    def test_welcome_auto_summary_config_persisted_and_emitted(self):
        widget = WelcomeWidget(_FakeDB())
        try:
            widget.auto_summary_check.setChecked(True)

            emitted = []
            widget.new_recording_requested.connect(lambda cfg: emitted.append(cfg))
            widget.rec_btn.click()

            self.assertEqual(len(emitted), 1)
            self.assertTrue(emitted[0].get("auto_summarize_after_transcription"))

            widget.auto_summary_check.setChecked(False)
            self.assertFalse(widget.auto_summary_check.isChecked())
        finally:
            widget.deleteLater()

    def test_welcome_uses_scroll_area_container(self):
        widget = WelcomeWidget(_FakeDB())
        try:
            self.assertTrue(hasattr(widget, "scroll_area"))
            self.assertTrue(widget.scroll_area.widgetResizable())
            self.assertIsNotNone(widget.scroll_area.widget())
        finally:
            widget.deleteLater()

    def test_welcome_compact_layout_reduces_key_heights(self):
        widget = WelcomeWidget(_FakeDB())
        try:
            widget._apply_layout_density(viewport_height=720)
            self.assertTrue(widget._compact_mode_active)
            self.assertEqual(widget.config_group.height(), 142)
            self.assertEqual(widget.rec_container.height(), 142)
            self.assertEqual(widget.chat_btn.height(), 52)
            self.assertEqual(widget.today_list.maximumHeight(), 170)

            widget._apply_layout_density(viewport_height=1200)
            self.assertFalse(widget._compact_mode_active)
            self.assertEqual(widget.config_group.height(), 160)
            self.assertEqual(widget.rec_container.height(), 160)
            self.assertEqual(widget.chat_btn.height(), 60)
            self.assertEqual(widget.today_list.maximumHeight(), 220)
        finally:
            widget.deleteLater()


class TestMainWindowDailySummaryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
        cls._qsettings_dir = tempfile.mkdtemp(prefix="secretario_qsettings_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            cls._qsettings_dir,
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_qsettings_dir") and os.path.isdir(cls._qsettings_dir):
            shutil.rmtree(cls._qsettings_dir, ignore_errors=True)

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

    def test_right_sidebar_accordion_and_tags_section(self):
        self.mock_db.get_all_tags.return_value = ["alpha", "beta"]
        self.window.load_collections()

        self.assertIn("tags", self.window._right_sidebar_sections)
        self.assertEqual(self.window.collections_list.count(), 2)
        self.assertEqual(self.window.collections_list.item(0).text(), "alpha")

        self.window._set_active_right_section("tags")
        for key, section in self.window._right_sidebar_sections.items():
            self.assertEqual(not section["content"].isHidden(), key == "tags")
            idx = section.get("index")
            self.assertEqual(self.window._right_sidebar_layout.stretch(idx), 1 if key == "tags" else 0)
        self.assertEqual(
            self.window._right_sidebar_layout.stretch(self.window._right_sidebar_bottom_spacer_index),
            0,
        )

        self.window._right_sidebar_sections["chats"]["header"].click()
        for key, section in self.window._right_sidebar_sections.items():
            self.assertEqual(not section["content"].isHidden(), key == "chats")
            idx = section.get("index")
            self.assertEqual(self.window._right_sidebar_layout.stretch(idx), 1 if key == "chats" else 0)
        self.assertEqual(
            self.window._right_sidebar_layout.stretch(self.window._right_sidebar_bottom_spacer_index),
            0,
        )

        # Click active section again -> collapse all
        self.window._right_sidebar_sections["chats"]["header"].click()
        self.assertIsNone(self.window._active_right_section)
        for key, section in self.window._right_sidebar_sections.items():
            self.assertTrue(section["content"].isHidden())
            idx = section.get("index")
            self.assertEqual(self.window._right_sidebar_layout.stretch(idx), 0)
            self.assertEqual(section["header"].property("class"), "accordion-header-btn")
        self.assertEqual(
            self.window._right_sidebar_layout.stretch(self.window._right_sidebar_bottom_spacer_index),
            1,
        )

    def test_right_settings_section_opens_settings_tab(self):
        self.assertTrue(hasattr(self.window, "right_settings_btn"))
        self.assertNotIn("settings", self.window._right_sidebar_sections)
        self.window.right_settings_btn.click()

        current = self.window.central_tabs.currentWidget()
        self.assertIsInstance(current, SettingsWidget)

    def test_tasks_sidebar_compact_item_and_tag_colors(self):
        self.mock_db.get_recent_incomplete_tasks.return_value = [
            {
                "id": 99,
                "record_id": 1,
                "content": "Prepare kickoff plan for next sprint",
                "record_tags": "alpha, beta",
                "tags": "",
                "is_completed": 0,
            }
        ]
        self.window.refresh_tasks_sidebar()

        item = self.window.tasks_sidebar_list.item(0)
        widget = self.window.tasks_sidebar_list.itemWidget(item)
        self.assertIsInstance(widget, SidebarTaskCompactWidget)
        self.assertIn("Prepare kickoff plan", widget.title_label.text())
        self.assertEqual(len(widget.tag_chips), 2)
        self.assertGreaterEqual(widget.minimumHeight(), 46)
        widget.complete_check.setChecked(True)
        self.mock_db.toggle_task_completion.assert_called_with(99, True)

        chip_a = create_tag_chip("alpha")
        chip_b = create_tag_chip("alpha")
        chip_c = create_tag_chip("beta")
        self.assertEqual(chip_a.styleSheet(), chip_b.styleSheet())
        self.assertNotEqual(chip_a.styleSheet(), chip_c.styleSheet())

    def test_startup_option_enqueues_missing_previous_weekly_summary(self):
        with patch("src.ui.main_window.QSettings") as mock_settings_cls:
            mock_settings = mock_settings_cls.return_value
            mock_settings.value.side_effect = lambda key, default=None, type=None: (
                True if key == "startup_enqueue_last_weekly_summary" else default
            )
            self.window.summary_task_queue.enqueue_weekly_summary = MagicMock()
            self.mock_db.get_weekly_summary.return_value = None
            self.mock_db.fetch_by_date_range.return_value = [
                {
                    "title": "Weekly Sync",
                    "created_at": "2026-02-24 10:00:00",
                    "transcription": "transcription text",
                    "recording_notes": "note text",
                }
            ]
            self.mock_db.compose_ai_text.return_value = "combined text"

            self.window._enqueue_missing_previous_week_summary_if_enabled()

            today = date.today()
            current_week_monday = today - timedelta(days=today.weekday())
            previous_week_monday = current_week_monday - timedelta(days=7)
            expected_sunday = (previous_week_monday + timedelta(days=6)).isoformat()

            self.window.summary_task_queue.enqueue_weekly_summary.assert_called_once()
            call_args = self.window.summary_task_queue.enqueue_weekly_summary.call_args.args
            self.assertEqual(call_args[0], expected_sunday)
            self.assertIn("combined text", call_args[1])
            self.assertEqual(call_args[2], "")

    def test_startup_option_enqueues_latest_missing_previous_daily_summary(self):
        with patch("src.ui.main_window.QSettings") as mock_settings_cls:
            mock_settings = mock_settings_cls.return_value
            mock_settings.value.side_effect = lambda key, default=None, type=None: (
                True if key == "startup_enqueue_previous_daily_summary" else default
            )
            self.window.summary_task_queue.enqueue_daily_summary = MagicMock()
            self.mock_db.get_latest_recording_day_without_daily_summary.return_value = "2026-02-27"

            self.window._enqueue_missing_previous_daily_summary_if_enabled()

            self.window.summary_task_queue.enqueue_daily_summary.assert_called_once_with(
                {
                    "date": "2026-02-27",
                    "tags_filter": "",
                }
            )

    def test_format_task_name_covers_supported_types(self):
        self.assertEqual(
            self.window._format_task_name({"type": "summary", "title": "Rec 1"}),
            "Recording: Rec 1",
        )
        self.assertEqual(
            self.window._format_task_name({"type": "task_extraction", "title": "Rec 2"}),
            "Tasks: Rec 2",
        )
        self.assertEqual(
            self.window._format_task_name({"type": "transcription", "title": "Rec 3"}),
            "Transcribing: Rec 3",
        )
        self.assertEqual(
            self.window._format_task_name({"type": "weekly_summary", "date": "2026-03-01"}),
            "Week: 2026-03-01",
        )
        self.assertEqual(
            self.window._format_task_name({"type": "daily_summary", "date": "2026-03-02", "tags_filter": "ops"}),
            "Day: 2026-03-02 [ops]",
        )
        self.assertEqual(
            self.window._format_task_name({"type": "daily_summary", "date": "2026-03-02"}),
            "Day: 2026-03-02",
        )

    def test_queue_changed_and_progress_handling(self):
        self.window.refresh_tasks_sidebar = MagicMock()

        self.window._on_summary_queue_changed(3, True)
        self.window.refresh_tasks_sidebar.assert_called()
        self.assertEqual(self.window.task_queue_progress.minimum(), 0)
        self.assertEqual(self.window.task_queue_progress.maximum(), 0)

        self.window._on_summary_queue_changed(0, False)
        self.assertEqual(self.window.task_queue_progress.minimum(), 0)
        self.assertEqual(self.window.task_queue_progress.maximum(), 1)
        self.assertEqual(self.window.task_queue_progress.value(), 0)
        self.assertEqual(self.window.task_status_label.text(), "Summary queue idle.")

        self.window.summary_task_queue._current_worker = None
        self.window.handle_progress(-1)
        self.assertEqual(self.window.task_queue_progress.maximum(), 0)

        self.window.handle_progress(-2)
        self.assertEqual(self.window.task_queue_progress.maximum(), 1)
        self.assertEqual(self.window.task_queue_progress.value(), 0)

        self.window.handle_progress(77)
        self.assertEqual(self.window.task_queue_progress.maximum(), 100)
        self.assertEqual(self.window.task_queue_progress.value(), 77)

        running_worker = MagicMock()
        running_worker.isRunning.return_value = False
        self.window.summary_task_queue._current_worker = running_worker
        self.window.task_queue_progress.setValue(33)
        self.window.handle_progress(88)
        self.assertEqual(self.window.task_queue_progress.value(), 33)

    def test_handle_status_message_respects_running_queue(self):
        self.window.summary_task_queue._current_worker = None
        self.window.handle_status_message("idle-msg")
        self.assertEqual(self.window.task_status_label.text(), "idle-msg")

        running_worker = MagicMock()
        running_worker.isRunning.return_value = False
        self.window.summary_task_queue._current_worker = running_worker
        self.window.handle_status_message("should-not-overwrite")
        self.assertEqual(self.window.task_status_label.text(), "idle-msg")


if __name__ == "__main__":
    unittest.main()
