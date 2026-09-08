from PyQt6.QtWidgets import QLineEdit, QListWidget

from src.ui.recording_in_progress.workspace import (
    add_quick_task,
    quick_task_contents,
    remove_selected_quick_tasks,
)


def test_workspace_adds_normalized_tasks_and_removes_selected_rows(qtbot):
    task_input = QLineEdit("  Follow up with legal  ")
    task_list = QListWidget()
    qtbot.addWidget(task_input)
    qtbot.addWidget(task_list)

    assert add_quick_task(task_input, task_list) is True
    assert add_quick_task(task_input, task_list) is False
    task_list.addItem("  ")
    assert quick_task_contents(task_list) == ["Follow up with legal"]

    task_list.item(0).setSelected(True)
    remove_selected_quick_tasks(task_list)
    assert quick_task_contents(task_list) == []
