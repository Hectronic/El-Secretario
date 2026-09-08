"""Qt list presentation and selection helpers for the task board."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from src.ui.components import TaskRowWidget


def render_task_rows(tasks_list, tasks, on_status_changed):
    """Replace list contents with rows while preserving task metadata contracts."""
    tasks_list.clear()
    if not tasks:
        tasks_list.addItem("No tasks.")
        return 0

    for task in tasks:
        display_task = dict(task)
        display_task["source_type"] = display_task.get("record_type")
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, display_task)
        tasks_list.addItem(item)

        row_widget = TaskRowWidget(display_task)
        row_widget.status_changed.connect(on_status_changed)
        item.setSizeHint(row_widget.sizeHint())
        tasks_list.setItemWidget(item, row_widget)
    return len(tasks)


def selected_task_items(tasks_list):
    """Return selected rows with persisted task identifiers only."""
    return [
        item
        for item in tasks_list.selectedItems()
        if isinstance(item.data(Qt.ItemDataRole.UserRole), dict)
        and isinstance(item.data(Qt.ItemDataRole.UserRole).get("id"), int)
    ]


def selected_or_current_task_items(tasks_list):
    """Use the current row as a single-item fallback for toolbar actions."""
    items = selected_task_items(tasks_list)
    if items:
        return items
    item = tasks_list.currentItem()
    task = item.data(Qt.ItemDataRole.UserRole) if item else None
    return [item] if isinstance(task, dict) and isinstance(task.get("id"), int) else []


def ordered_task_ids(tasks_list):
    """Return persisted task IDs in their visible order, excluding placeholders."""
    task_ids = []
    for index in range(tasks_list.count()):
        task = tasks_list.item(index).data(Qt.ItemDataRole.UserRole)
        if isinstance(task, dict) and isinstance(task.get("id"), int):
            task_ids.append(int(task["id"]))
    return task_ids


def apply_completion_state(tasks_list, items, completed_state):
    """Update visible rows after their persisted completion state has changed."""
    for item in items:
        task = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            continue
        widget = tasks_list.itemWidget(item)
        if isinstance(widget, TaskRowWidget):
            widget.set_completed(completed_state)
        task = dict(task)
        task["is_completed"] = completed_state
        item.setData(Qt.ItemDataRole.UserRole, task)
