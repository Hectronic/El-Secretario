from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidget

from src.ui.tasks.presentation import (
    apply_completion_state,
    ordered_task_ids,
    render_task_rows,
    selected_or_current_task_items,
    selected_task_items,
)


def test_render_task_rows_copies_metadata_and_keeps_original_task_unchanged(qtbot):
    task_list = QListWidget()
    qtbot.addWidget(task_list)
    source_task = {"id": 5, "content": "Review release", "record_type": "meeting"}

    count = render_task_rows(task_list, [source_task], lambda *_args: None)

    rendered = task_list.item(0).data(Qt.ItemDataRole.UserRole)
    assert count == 1
    assert rendered["source_type"] == "meeting"
    assert "source_type" not in source_task


def test_selection_helpers_and_completion_state_ignore_placeholder_rows(qtbot):
    task_list = QListWidget()
    qtbot.addWidget(task_list)
    render_task_rows(
        task_list,
        [
            {"id": 4, "content": "First", "is_completed": 0},
            {"id": 2, "content": "Second", "is_completed": 0},
        ],
        lambda *_args: None,
    )
    first_item = task_list.item(0)
    first_item.setSelected(True)

    assert selected_task_items(task_list) == [first_item]
    assert selected_or_current_task_items(task_list) == [first_item]
    assert ordered_task_ids(task_list) == [4, 2]

    apply_completion_state(task_list, [first_item], True)
    assert first_item.data(Qt.ItemDataRole.UserRole)["is_completed"] is True
