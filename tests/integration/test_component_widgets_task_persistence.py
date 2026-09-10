"""Real Qt-to-SQLite contract for the extracted task row widgets."""

from src.database import DBManager
from src.ui.tasks_list_widget import TasksListWidget


def test_task_row_completion_persists_through_task_board(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "component-widgets.sqlite"))
    task_id = db.save_task(
        record_id=None,
        content="Validate component boundary",
        tags="quality",
        day_date="2026-09-09",
    )
    widget = TasksListWidget(db, filter_date="2026-09-09")
    qtbot.addWidget(widget)
    changes = []
    widget.tasks_changed.connect(lambda: changes.append(True))

    row = widget.tasks_list.itemWidget(widget.tasks_list.item(0))
    row.status_btn.click()

    saved = next(task for task in db.get_tasks_by_date("2026-09-09") if task["id"] == task_id)
    assert saved["is_completed"] == 1
    assert changes == [True]
