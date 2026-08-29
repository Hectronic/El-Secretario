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

from unittest.mock import MagicMock

import pytest
from PyQt6.QtWidgets import QLabel

from src.ui.main_window.summary_queue_status import SummaryQueueStatusCoordinator


@pytest.mark.parametrize(
    ("task", "expected"),
    [
        ({"type": "summary", "title": "Planning"}, "Recording: Planning"),
        ({"type": "task_extraction", "title": "Planning"}, "Tasks: Planning"),
        ({"type": "transcription", "title": "Planning"}, "Transcribing: Planning"),
        ({"type": "weekly_summary", "date": "2026-05-17"}, "Week: 2026-05-17"),
        (
            {"type": "daily_summary", "date": "2026-05-18", "tags_filter": "work"},
            "Day: 2026-05-18 [work]",
        ),
        ({"type": "rag_reindex", "reindex_scope": "missing"}, "RAG Reindex (Missing)"),
    ],
)
def test_format_task_name_preserves_queue_labels(task, expected):
    assert SummaryQueueStatusCoordinator.format_task_name(task) == expected


def test_refresh_metrics_uses_queue_runtime_stats(qtbot):
    window = MagicMock()
    window.summary_task_queue.get_runtime_stats.return_value = {
        "running": 1,
        "pending": 2,
        "finished": 3,
        "failed": 4,
        "skipped": 5,
    }
    window.task_metrics_label = QLabel()
    qtbot.addWidget(window.task_metrics_label)

    SummaryQueueStatusCoordinator(window).refresh_task_metrics()

    assert window.task_metrics_label.text() == "Q r1 p2 f3 e4 s5"


def test_handle_status_message_falls_back_before_status_widgets_exist():
    window = MagicMock(spec=["summary_task_queue", "statusBar"])
    window.summary_task_queue.is_running = False
    status_bar = MagicMock()
    window.statusBar.return_value = status_bar

    SummaryQueueStatusCoordinator(window).handle_status_message("Booting")

    status_bar.showMessage.assert_called_once_with("Booting", 5000)
