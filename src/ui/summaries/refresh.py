"""Refresh policies for task and recording sections of a summary viewer."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from src.ui.summaries.widgets import WeeklyRecordingRowWidget
from src.ui.summaries.context import summary_date_range, summary_tags


def refresh_daily_task_boards(viewer):
    date_ref = viewer.summary_data.get("date")
    tags_filter = viewer.summary_data.get("tags_filter")
    for name in ("daily_created_board", "daily_completed_board"):
        if hasattr(viewer, name):
            board = getattr(viewer, name)
            board.snapshot_ref = date_ref
            board.global_tags_filter = tags_filter
            board.refresh()


def refresh_weekly_task_snapshot(viewer):
    if not hasattr(viewer, "weekly_task_boards"):
        return
    week_start = viewer.summary_data.get("week_start")
    tags_filter = viewer.summary_data.get("tags_filter")
    snapshot = viewer.db.get_weekly_task_snapshot(week_start, tags_filter) if (viewer.db and week_start) else {}
    keys = {"week_created": "created_this_week", "week_completed": "completed_this_week", "week_pending_before": "pending_from_before"}
    labels = {"week_created": "Created", "week_completed": "Completed", "week_pending_before": "Pending From Before"}
    for mode, board in viewer.weekly_task_boards.items():
        board.snapshot_ref = week_start
        board.global_tags_filter = tags_filter
        board.refresh()
        if hasattr(viewer, "weekly_tasks_tabs"):
            index = viewer.weekly_tasks_tabs.indexOf(board)
            if index >= 0:
                viewer.weekly_tasks_tabs.setTabText(index, f"{labels.get(mode, mode)} ({len(snapshot.get(keys.get(mode, ''), []))})")


def refresh_weekly_recordings(viewer):
    if not viewer.db or not hasattr(viewer, "weekly_recordings_list"):
        return
    start, end = summary_date_range(viewer.summary_data)
    if not start:
        return
    records = viewer.db.fetch_by_date_range(start, end, tags=summary_tags(viewer.summary_data))
    viewer.weekly_recordings_list.clear()
    viewer.weekly_recordings_meta.setText(f"{len(records)} recording(s) in scope")
    if not records:
        viewer.weekly_recordings_list.addItem(QListWidgetItem("No recordings found for this week."))
        return
    for record in records:
        item = QListWidgetItem()
        row = WeeklyRecordingRowWidget(record, viewer)
        row.open_requested.connect(viewer.open_recording_requested.emit)
        item.setSizeHint(row.sizeHint())
        item.setData(Qt.ItemDataRole.UserRole, record)
        viewer.weekly_recordings_list.addItem(item)
        viewer.weekly_recordings_list.setItemWidget(item, row)
