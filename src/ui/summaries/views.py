"""Daily and weekly summary-view composition helpers."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QTabWidget, QVBoxLayout, QWidget

from src.ui.tasks_list_widget import TasksListWidget
from .widgets import AutoSizingMarkdownView


def _task_board(viewer, mode, ref):
    board = TasksListWidget(viewer.db, show_controls=False, snapshot_mode=mode, snapshot_ref=ref, parent=viewer)
    board.global_tags_filter = viewer.summary_data.get("tags_filter")
    board.open_recording_requested.connect(viewer.open_recording_requested.emit)
    return board


def build_daily_tabs(viewer, root_layout):
    viewer.summary_tabs = QTabWidget()
    general = QWidget(); layout = QVBoxLayout(general); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(8)
    viewer.content_area = AutoSizingMarkdownView(); viewer.content_area.setMarkdown(viewer.summary_data.get("summary", "")); viewer.content_area.setStyleSheet("font-size: 14px; line-height: 1.7;background: transparent; border: none; padding: 0;"); layout.addWidget(viewer.content_area)
    viewer.summary_tabs.addTab(general, "General")
    ref = viewer.summary_data.get("date")
    viewer.daily_created_board = _task_board(viewer, "day_created", ref); viewer.summary_tabs.addTab(viewer.daily_created_board, "Created Today")
    viewer.daily_completed_board = _task_board(viewer, "day_completed", ref); viewer.summary_tabs.addTab(viewer.daily_completed_board, "Completed Today")
    root_layout.addWidget(viewer.summary_tabs, 1); viewer._refresh_daily_task_boards()


def build_weekly_overview(viewer, root_layout):
    card = QFrame(); card.setObjectName("weeklySummaryCard"); card.setStyleSheet("QFrame#weeklySummaryCard { background-color: rgba(127, 127, 127, 0.06); border: 1px solid rgba(127, 127, 127, 0.22); border-radius: 18px; }")
    layout = QVBoxLayout(card); layout.setContentsMargins(22, 20, 22, 20); layout.setSpacing(10)
    for text, style in [("Weekly Narrative", "font-size: 11px; font-weight: 700; color: palette(highlight);"), ("What mattered this week", "font-size: 26px; font-weight: 800;"), ("A focused digest of progress, decisions, and follow-up work.", "font-size: 13px; color: palette(mid);")]:
        label = QLabel(text); label.setStyleSheet(style); layout.addWidget(label)
    viewer.content_area = AutoSizingMarkdownView(); viewer.content_area.setMarkdown(viewer.summary_data.get("summary", "")); viewer.content_area.setStyleSheet("font-size: 15px; line-height: 1.8; background-color: rgba(127, 127, 127, 0.04); border: 1px solid rgba(127, 127, 127, 0.16); border-radius: 14px; padding: 10px 12px;"); layout.addWidget(viewer.content_area); root_layout.addWidget(card, 3)
    tasks = QWidget(); tasks_layout = QVBoxLayout(tasks); tasks_layout.setContentsMargins(0, 0, 0, 0); tasks_layout.setSpacing(10); title = QLabel("Tasks"); title.setStyleSheet("font-size: 18px; font-weight: 700;"); tasks_layout.addWidget(title); build_weekly_task_tabs(viewer, tasks_layout); root_layout.addWidget(tasks, 2)
    recordings = QWidget(); recordings_layout = QVBoxLayout(recordings); recordings_layout.setContentsMargins(0, 0, 0, 0); recordings_layout.setSpacing(10); title = QLabel("Recordings This Week"); title.setStyleSheet("font-size: 18px; font-weight: 700;"); recordings_layout.addWidget(title)
    viewer.weekly_recordings_meta = QLabel(""); viewer.weekly_recordings_meta.setStyleSheet("font-size: 12px; color: palette(mid);"); recordings_layout.addWidget(viewer.weekly_recordings_meta)
    viewer.weekly_recordings_list = QListWidget(); viewer.weekly_recordings_list.setProperty("class", "embedded-list"); viewer.weekly_recordings_list.setSpacing(8); viewer.weekly_recordings_list.setMinimumHeight(420); recordings_layout.addWidget(viewer.weekly_recordings_list, 1); root_layout.addWidget(recordings, 2)
    viewer._load_weekly_tasks_snapshot(); viewer._load_weekly_recordings()


def build_weekly_task_tabs(viewer, root_layout):
    viewer.weekly_tasks_tabs = QTabWidget(); viewer.weekly_task_boards = {}
    for mode, label in [("week_created", "Created"), ("week_completed", "Completed"), ("week_pending_before", "Pending From Before")]:
        board = _task_board(viewer, mode, viewer.summary_data.get("week_start")); board.setMinimumHeight(360); viewer.weekly_tasks_tabs.addTab(board, label); viewer.weekly_task_boards[mode] = board
    viewer.weekly_tasks_tabs.setMinimumHeight(420); root_layout.addWidget(viewer.weekly_tasks_tabs, 1)
