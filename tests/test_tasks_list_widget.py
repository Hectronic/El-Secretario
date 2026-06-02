from datetime import date
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import QListWidgetItem

from src.ui.tasks_list_widget import TasksListWidget


class _FakeDB:
    def __init__(self):
        self.saved_task_calls = []
        self.update_details_calls = []
        self.toggle_calls = []
        self.custom_order_calls = []
        self.by_range_calls = []
        self.daily_snapshot_calls = []
        self.weekly_snapshot_calls = []

    def get_all_tags(self):
        return ["alpha", "beta", "ops"]

    def _week_sunday(self, day_date):
        return "2099-12-31"

    def save_task(self, **kwargs):
        self.saved_task_calls.append(kwargs)
        return 1

    def update_task_details(self, task_id, content, notes, tags):
        self.update_details_calls.append((task_id, content, notes, tags))

    def get_tasks_for_board(self, order_mode="date", include_completed=False, limit=None):
        return []

    def get_tasks_by_date(self, date_str, tags_filter=None, order_mode="date"):
        return []

    def get_tasks_by_date_range(self, start_date, end_date, tags_filter=None, order_mode="date", include_completed=False):
        self.by_range_calls.append((start_date, end_date, tags_filter, order_mode, include_completed))
        return []

    def get_tasks_by_record(self, record_id):
        return []

    def toggle_task_completion(self, task_id, is_completed):
        self.toggle_calls.append((task_id, is_completed))
        return None

    def set_tasks_custom_order(self, ordered_task_ids):
        self.custom_order_calls.append(list(ordered_task_ids))
        return None

    def delete_task(self, task_id):
        return None

    def get_daily_task_snapshot(self, day_ref, tags_filter):
        self.daily_snapshot_calls.append((day_ref, tags_filter))
        return {
            "created_this_day": [
                {"id": 1, "content": "Created today", "is_completed": 0, "tags": "alpha", "day_date": day_ref}
            ],
            "completed_this_day": [
                {"id": 2, "content": "Completed today", "is_completed": 1, "tags": "beta", "day_date": day_ref}
            ],
        }

    def get_weekly_task_snapshot(self, week_ref, tags_filter):
        self.weekly_snapshot_calls.append((week_ref, tags_filter))
        return {
            "created_this_week": [
                {"id": 3, "content": "Created week", "is_completed": 0, "tags": "alpha", "day_date": week_ref}
            ],
            "completed_this_week": [
                {"id": 4, "content": "Completed week", "is_completed": 1, "tags": "beta", "day_date": week_ref}
            ],
            "pending_from_before": [
                {"id": 5, "content": "Pending old", "is_completed": 0, "tags": "ops", "day_date": week_ref}
            ],
        }


class _DialogAccepted:
    class DialogCode:
        Accepted = 1

    def __init__(self, db, parent=None, title="Task", task_data=None):
        self._content = "Task from dialog"
        self._notes = "Notes from dialog"
        self._tags = "alpha, beta"

    def exec(self):
        return self.DialogCode.Accepted

    def get_content(self):
        return self._content

    def get_notes(self):
        return self._notes

    def get_tags(self):
        return self._tags


class _DialogRejected(_DialogAccepted):
    def exec(self):
        return 0


def test_open_create_dialog_saves_tags_notes_and_content(qtbot):
    db = _FakeDB()
    widget = TasksListWidget(db)
    qtbot.addWidget(widget)
    sidebar = MagicMock()

    with patch("src.ui.tasks_list_widget.TaskEditDialog", _DialogAccepted), patch(
        "src.ui.tasks_list_widget.QApplication.topLevelWidgets",
        return_value=[sidebar],
    ):
        widget.open_create_dialog()

    assert len(db.saved_task_calls) == 1
    payload = db.saved_task_calls[0]
    assert payload["content"] == "Task from dialog"
    assert payload["notes"] == "Notes from dialog"
    assert payload["tags"] == "alpha, beta"
    assert payload["record_id"] is None
    assert payload["day_date"] == date.today().isoformat()
    sidebar.refresh_tasks_sidebar.assert_called_once()


def test_edit_task_item_updates_task_details_with_tags(qtbot):
    db = _FakeDB()
    widget = TasksListWidget(db)
    qtbot.addWidget(widget)

    task = {"id": 42, "content": "Old", "notes": "Old note", "tags": "ops"}
    item = QListWidgetItem()
    item.setData(Qt.ItemDataRole.UserRole, task)

    with patch("src.ui.tasks_list_widget.TaskEditDialog", _DialogAccepted):
        widget._edit_task_item(item)

    assert db.update_details_calls == [(42, "Task from dialog", "Notes from dialog", "alpha, beta")]


def test_edit_task_item_cancel_does_not_update(qtbot):
    db = _FakeDB()
    widget = TasksListWidget(db)
    qtbot.addWidget(widget)

    task = {"id": 10, "content": "Old"}
    item = QListWidgetItem()
    item.setData(Qt.ItemDataRole.UserRole, task)

    with patch("src.ui.tasks_list_widget.TaskEditDialog", _DialogRejected):
        widget._edit_task_item(item)

    assert db.update_details_calls == []


def test_global_filter_precedence_over_local_tag(qtbot):
    db = _FakeDB()
    widget = TasksListWidget(db)
    qtbot.addWidget(widget)

    widget.tag_filter_combo.setCurrentText("beta")
    widget.set_global_filters(
        week_monday=QDate(2026, 3, 2),
        date_filter="2026-03-08",
        tags_filter="alpha",
    )

    assert widget.tag_filter_combo.isEnabled() is False
    assert db.by_range_calls, "Expected range query call"
    _, _, tags_filter, _, _ = db.by_range_calls[-1]
    assert tags_filter == "alpha"


def test_global_filters_accept_qdate_python_date_and_string(qtbot):
    db = _FakeDB()
    widget = TasksListWidget(db)
    qtbot.addWidget(widget)

    widget.set_global_filters(week_monday=QDate(2026, 3, 2), date_filter=QDate(2026, 3, 5))
    assert db.by_range_calls[-1][:2] == ("2026-03-02", "2026-03-05")

    widget.set_global_filters(week_monday=date(2026, 3, 2), date_filter=None)
    assert db.by_range_calls[-1][:2] == ("2026-03-02", "2026-03-08")

    widget.set_global_filters(week_monday="2026-03-02", date_filter="2026-03-05")
    assert db.by_range_calls[-1][:2] == ("2026-03-02", "2026-03-05")


def test_refresh_snapshot_modes(qtbot):
    db = _FakeDB()

    created = TasksListWidget(db, snapshot_mode="day_created", snapshot_ref="2026-03-01")
    qtbot.addWidget(created)
    assert db.daily_snapshot_calls[-1] == ("2026-03-01", None)
    task = created.tasks_list.item(0).data(Qt.ItemDataRole.UserRole)
    assert task["id"] == 1

    completed = TasksListWidget(db, snapshot_mode="day_completed", snapshot_ref="2026-03-01")
    qtbot.addWidget(completed)
    task = completed.tasks_list.item(0).data(Qt.ItemDataRole.UserRole)
    assert task["id"] == 2

    week_pending = TasksListWidget(db, snapshot_mode="week_pending_before", snapshot_ref="2026-03-02")
    qtbot.addWidget(week_pending)
    assert db.weekly_snapshot_calls[-1] == ("2026-03-02", None)
    task = week_pending.tasks_list.item(0).data(Qt.ItemDataRole.UserRole)
    assert task["id"] == 5


def test_on_list_reordered_sets_custom_order(qtbot):
    db = _FakeDB()
    widget = TasksListWidget(db)
    qtbot.addWidget(widget)
    sidebar = MagicMock()

    for task_id in (10, 11):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, {"id": task_id, "content": f"T{task_id}", "is_completed": 0})
        widget.tasks_list.addItem(item)

    with patch("src.ui.tasks_list_widget.QApplication.topLevelWidgets", return_value=[sidebar]):
        widget._on_list_reordered()

    assert widget.order_combo.currentData() == "custom"
    assert db.custom_order_calls[-1] == [10, 11]
    sidebar.refresh_tasks_sidebar.assert_called_once()


def test_complete_selected_toggles_all_selected(qtbot):
    db = _FakeDB()
    widget = TasksListWidget(db)
    qtbot.addWidget(widget)
    widget.tasks_list.clear()

    item_a = QListWidgetItem()
    item_a.setData(Qt.ItemDataRole.UserRole, {"id": 21, "content": "A", "is_completed": 0})
    widget.tasks_list.addItem(item_a)
    item_b = QListWidgetItem()
    item_b.setData(Qt.ItemDataRole.UserRole, {"id": 22, "content": "B", "is_completed": 0})
    widget.tasks_list.addItem(item_b)

    item_a.setSelected(True)
    item_b.setSelected(True)
    widget._complete_selected()

    assert (21, True) in db.toggle_calls
    assert (22, True) in db.toggle_calls


def test_single_complete_toggle_refreshes_global_sidebar(qtbot):
    db = _FakeDB()
    widget = TasksListWidget(db)
    qtbot.addWidget(widget)
    sidebar = MagicMock()

    with patch("src.ui.tasks_list_widget.QApplication.topLevelWidgets", return_value=[sidebar]):
        widget._on_single_complete_toggle(77, True)

    assert db.toggle_calls == [(77, True)]
    sidebar.refresh_tasks_sidebar.assert_called_once()
