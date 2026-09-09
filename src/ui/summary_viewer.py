"""Compatible Qt facade for daily and weekly summary views."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from src.ui.summaries.context import build_week_chat_contexts, summary_date_range, summary_tags
from src.ui.summaries.views import build_daily_tabs, build_weekly_overview, build_weekly_task_tabs
from src.ui.summaries.widgets import AutoSizingMarkdownView, WeeklyRecordingRowWidget


class SummaryViewerWidget(QWidget):
    """Qt shell; composition, refresh and context policy live in ``ui.summaries``."""

    close_requested = pyqtSignal()
    regenerate_requested = pyqtSignal(dict)
    open_recording_requested = pyqtSignal(int)
    start_chat_requested = pyqtSignal(str, list)
    start_chat_contexts_requested = pyqtSignal(list, bool)

    def __init__(self, summary_data, db=None, task_queue=None, parent=None):
        super().__init__(parent)
        self.summary_data = summary_data
        self.db = db
        self.task_queue = task_queue
        self.init_ui()

    def init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 12, 20, 0)
        outer.setSpacing(8)
        top = QHBoxLayout(); top.addStretch()
        self.weekly_chat_btn = None
        if self.summary_data.get("type") == "weekly":
            self.weekly_chat_btn = QPushButton("💬 Chat This Week")
            self.weekly_chat_btn.setToolTip("Open this week's chat in a floating window")
            self.weekly_chat_btn.setProperty("class", "calendar-primary-btn")
            self.weekly_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.weekly_chat_btn.setMinimumSize(180, 38)
            self.weekly_chat_btn.clicked.connect(self._open_week_chat)
            top.addWidget(self.weekly_chat_btn, 0, Qt.AlignmentFlag.AlignRight)
        outer.addLayout(top)
        scroll = QScrollArea(self); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); outer.addWidget(scroll)
        page = QWidget(); scroll.setWidget(page)
        layout = QVBoxLayout(page); layout.setContentsMargins(0, 8, 0, 20); layout.setSpacing(15)
        is_daily = self.summary_data.get("type", "daily") == "daily"
        title = f"📅 Daily Summary - {self.summary_data.get('date')}" if is_daily else f"Week Summary - Week of {self.summary_data.get('week_start')}"
        heading = QHBoxLayout(); label = QLabel(title); label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;"); heading.addWidget(label); heading.addStretch(); layout.addLayout(heading)
        metadata = QHBoxLayout(); self.meta_label = QLabel(f"Generated at: {self.summary_data.get('generated_at', 'Unknown')}"); self.meta_label.setStyleSheet("color: #777; font-size: 12px;"); metadata.addWidget(self.meta_label); metadata.addStretch(); layout.addLayout(metadata)
        self._build_daily_tabs(layout) if is_daily else self._build_weekly_overview(layout)
        actions = QHBoxLayout()
        if is_daily:
            regenerate = QPushButton("↻ Regenerate Daily Summary"); regenerate.setToolTip("Regenerate this daily summary (will check for new recordings)"); self._style_action_button(regenerate); regenerate.clicked.connect(lambda: self.regenerate_requested.emit(self.summary_data)); actions.addWidget(regenerate); actions.addStretch()
            chat = QPushButton("💬 Chat this day"); chat.setToolTip("Open a chat filtered to this day"); self._style_action_button(chat); chat.clicked.connect(self._open_day_chat); actions.addWidget(chat)
        else: actions.addStretch()
        layout.addLayout(actions)

    # Compatibility hooks retained for extensions and existing callers.
    def _build_daily_tabs(self, layout): return build_daily_tabs(self, layout)
    def _build_weekly_overview(self, layout): return build_weekly_overview(self, layout)
    def _build_weekly_task_tabs(self, layout): return build_weekly_task_tabs(self, layout)

    def _load_weekly_tasks_snapshot(self):
        from src.ui.summaries.refresh import refresh_weekly_task_snapshot
        refresh_weekly_task_snapshot(self)

    def _load_weekly_recordings(self):
        from src.ui.summaries.refresh import refresh_weekly_recordings
        refresh_weekly_recordings(self)

    def _refresh_daily_task_boards(self):
        from src.ui.summaries.refresh import refresh_daily_task_boards
        refresh_daily_task_boards(self)

    def _get_summary_tags(self): return summary_tags(self.summary_data)
    def _get_batch_range(self): return summary_date_range(self.summary_data)
    def _open_day_chat(self):
        if date := self.summary_data.get("date"): self.start_chat_requested.emit(date, [])
    def _open_week_chat(self):
        if contexts := build_week_chat_contexts(self.summary_data, self.db): self.start_chat_contexts_requested.emit(contexts, True)
    def _style_action_button(self, button):
        button.setProperty("class", "calendar-nav-btn"); button.setCursor(Qt.CursorShape.PointingHandCursor); button.setMinimumHeight(34)
    def update_content(self, summary_data):
        self.summary_data = summary_data
        self.content_area.setMarkdown(summary_data.get("summary", ""))
        self.meta_label.setText(f"Generated at: {summary_data.get('generated_at', 'Unknown')}")
        self._refresh_daily_task_boards() if summary_data.get("type") == "daily" else (self._load_weekly_tasks_snapshot(), self._load_weekly_recordings())


__all__ = ["AutoSizingMarkdownView", "SummaryViewerWidget", "WeeklyRecordingRowWidget"]
