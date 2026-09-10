from datetime import date

from src.ui.tasks.actions import (
    create_manual_task,
    delete_tasks,
    save_custom_order,
    set_task_completion,
    update_task_details,
)


class _TaskPort:
    def __init__(self):
        self.created = []
        self.completed = []
        self.deleted = []
        self.updated = []
        self.order = []

    def _week_sunday(self, _day_date):
        return "2026-03-08"

    def save_task(self, **payload):
        self.created.append(payload)
        return 9

    def toggle_task_completion(self, task_id, state):
        self.completed.append((task_id, state))

    def delete_task(self, task_id):
        self.deleted.append(task_id)

    def update_task_details(self, task_id, content, notes, tags):
        self.updated.append((task_id, content, notes, tags))

    def set_tasks_custom_order(self, task_ids):
        self.order.append(task_ids)


def test_create_manual_task_keeps_day_and_week_context():
    db = _TaskPort()

    task_id = create_manual_task(
        db,
        record_id=None,
        filter_date="2026-03-07",
        content="Publish release notes",
        notes="After QA",
        tags="planning",
        today=date(2026, 3, 1),
    )

    assert task_id == 9
    assert db.created == [{
        "record_id": None,
        "content": "Publish release notes",
        "tags": "planning",
        "day_date": "2026-03-07",
        "week_start": "2026-03-08",
        "notes": "After QA",
    }]


def test_completion_and_deletion_apply_each_selected_task():
    db = _TaskPort()

    set_task_completion(db, [3, 5], True)
    delete_tasks(db, [5, 3])

    assert db.completed == [(3, True), (5, True)]
    assert db.deleted == [5, 3]


def test_update_and_reorder_actions_delegate_only_valid_order_payloads():
    db = _TaskPort()

    update_task_details(db, 7, "Revised", "With notes", "ops")
    save_custom_order(db, [])
    save_custom_order(db, [9, 7])

    assert db.updated == [(7, "Revised", "With notes", "ops")]
    assert db.order == [[9, 7]]
