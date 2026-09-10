from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from src.database import DBManager
from src.ui.tasks_list_widget import TasksListWidget


class _AcceptedCreateDialog:
    def __init__(self, *_args, **_kwargs):
        pass

    def exec(self):
        return QDialog.DialogCode.Accepted

    def get_content(self):
        return "Publish task board refactor"

    def get_notes(self):
        return "Validated through the board"

    def get_tags(self):
        return "planning"


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


def test_task_board_creation_and_reordering_persist_with_real_sqlite(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "tasks-board-actions.sqlite"))
    db.save_task(
        record_id=None,
        content="First task",
        day_date="2026-09-07",
    )
    db.save_task(
        record_id=None,
        content="Second task",
        day_date="2026-09-07",
    )
    widget = TasksListWidget(db, filter_date="2026-09-07")
    qtbot.addWidget(widget)
    changes = []
    widget.tasks_changed.connect(lambda: changes.append(True))

    monkeypatch.setattr("src.ui.tasks_list_widget.TaskEditDialog", _AcceptedCreateDialog)
    widget.open_create_dialog()

    created = [
        task for task in db.get_tasks_by_date("2026-09-07")
        if task["content"] == "Publish task board refactor"
    ]
    assert len(created) == 1
    assert created[0]["notes"] == "Validated through the board"
    assert created[0]["tags"] == "planning"

    visible_ids = [
        widget.tasks_list.item(index).data(Qt.ItemDataRole.UserRole)["id"]
        for index in range(widget.tasks_list.count())
    ]
    item = widget.tasks_list.takeItem(1)
    widget.tasks_list.insertItem(0, item)
    widget._on_list_reordered()

    ordered = db.get_tasks_by_date("2026-09-07", order_mode="custom")
    assert [task["id"] for task in ordered] == [visible_ids[1], visible_ids[0], visible_ids[2]]
    assert len(changes) == 2
