from PyQt6.QtCore import Qt

from src.database import DBManager
from src.ui.tasks_list_widget import TasksListWidget


def test_task_board_global_filter_and_completion_persist_with_real_sqlite(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "tasks-board.sqlite"))
    planning_task = db.save_task(
        record_id=None,
        content="Publish release notes",
        tags="planning",
        day_date="2026-09-07",
    )
    db.save_task(
        record_id=None,
        content="Investigate audio issue",
        tags="ops",
        day_date="2026-09-07",
    )
    widget = TasksListWidget(db)
    qtbot.addWidget(widget)
    changed = []
    widget.tasks_changed.connect(lambda: changed.append(True))

    widget.set_global_filters(date_filter="2026-09-07", tags_filter="planning")

    assert widget.tasks_list.count() == 1
    item = widget.tasks_list.item(0)
    assert item.data(Qt.ItemDataRole.UserRole)["id"] == planning_task
    item.setSelected(True)
    widget._complete_selected()

    persisted = db.get_tasks_for_board(include_completed=True)
    saved_task = next(task for task in persisted if task["id"] == planning_task)
    assert saved_task["is_completed"] == 1
    assert changed == [True]
