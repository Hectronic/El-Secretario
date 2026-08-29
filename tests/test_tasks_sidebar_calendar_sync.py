from unittest.mock import MagicMock

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QComboBox, QListWidget

from src.ui.main_window import MainWindow
from src.ui.components import SidebarTaskCompactWidget
from src.ui.main_window.sidebar_actions import SidebarActionsCoordinator


def test_refresh_tasks_sidebar_uses_calendar_range_filters(qtbot):
    window = MainWindow.__new__(MainWindow)
    window.db = MagicMock()
    window.sidebar_actions = SidebarActionsCoordinator(window)
    window.tasks_sidebar_list = QListWidget()
    qtbot.addWidget(window.tasks_sidebar_list)
    window.tasks_sidebar_limit = 20
    window.current_week_monday = QDate(2026, 3, 2)
    window.current_date_filter = "2026-03-05"

    window.tag_filter_combo = QComboBox()
    window.tag_filter_combo.addItems(["All", "work"])
    window.tag_filter_combo.setCurrentText("work")
    qtbot.addWidget(window.tag_filter_combo)

    window.db.get_tasks_by_date_range.return_value = [
        {
            "id": 1,
            "content": "Task in range",
            "tags": "work",
            "record_id": None,
            "is_completed": 0,
        }
    ]

    window.refresh_tasks_sidebar()

    window.db.get_tasks_by_date_range.assert_called_once_with(
        "2026-03-02",
        "2026-03-05",
        tags_filter="work",
        include_completed=False,
    )
    window.db.get_recent_incomplete_tasks.assert_not_called()
    assert window.tasks_sidebar_list.count() == 1


def test_sidebar_task_compact_widget_uses_uniform_height(qtbot):
    with_tags = SidebarTaskCompactWidget("Task with tags", ["work", "urgent"])
    without_tags = SidebarTaskCompactWidget("Task without tags", [])
    qtbot.addWidget(with_tags)
    qtbot.addWidget(without_tags)

    assert with_tags.height() == SidebarTaskCompactWidget.ROW_HEIGHT
    assert without_tags.height() == SidebarTaskCompactWidget.ROW_HEIGHT
    assert with_tags.sizeHint().height() == without_tags.sizeHint().height()
