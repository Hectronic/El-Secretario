from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QTextBrowser,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from src.ui.tasks_list_widget import TasksListWidget
from src.ui.components import create_tag_chip


class AutoSizingMarkdownView(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenExternalLinks(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizeAdjustPolicy(QTextBrowser.SizeAdjustPolicy.AdjustToContents)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().documentLayout().documentSizeChanged.connect(self._update_height)
        self._update_height()

    def setMarkdown(self, markdown):
        super().setMarkdown(markdown)
        self._update_height()

    def _update_height(self, *_args):
        doc_height = int(self.document().size().height())
        margins = self.contentsMargins()
        frame = self.frameWidth() * 2
        self.setMinimumHeight(max(140, doc_height + margins.top() + margins.bottom() + frame + 18))
        self.setMaximumHeight(max(140, doc_height + margins.top() + margins.bottom() + frame + 18))


class WeeklyRecordingRowWidget(QWidget):
    open_requested = pyqtSignal(int)

    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record or {}
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        text_col = QVBoxLayout()
        text_col.setSpacing(5)

        title = QLabel((self.record.get("title") or "Untitled recording").strip())
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        text_col.addWidget(title)

        created_at = str(self.record.get("created_at") or "").strip()
        duration = float(self.record.get("duration") or 0)
        meta_bits = [created_at[:16]] if created_at else []
        if duration > 0:
            meta_bits.append(f"{duration:.1f}s")
        if self.record.get("summary"):
            meta_bits.append("Summary ready")
        if self.record.get("is_favorite"):
            meta_bits.append("Favorite")
        meta = QLabel(" • ".join(meta_bits))
        meta.setStyleSheet("font-size: 11px; color: palette(mid);")
        text_col.addWidget(meta)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(4)
        tags = [t.strip() for t in str(self.record.get("tags") or "").split(",") if t.strip()]
        if tags:
            for tag in tags[:4]:
                chips_row.addWidget(create_tag_chip(tag, width=None, height=18, font_size=9, parent=self))
        else:
            empty = QLabel("No tags")
            empty.setStyleSheet("font-size: 10px; color: palette(mid);")
            chips_row.addWidget(empty)
        chips_row.addStretch()
        text_col.addLayout(chips_row)
        layout.addLayout(text_col, 1)

        open_btn = QPushButton("Open")
        open_btn.setProperty("class", "calendar-nav-btn")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setMinimumHeight(32)
        open_btn.clicked.connect(self._emit_open)
        layout.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.setStyleSheet(
            "background-color: palette(base);"
            "border: 1px solid palette(midlight);"
            "border-radius: 14px;"
        )

    def _emit_open(self):
        rec_id = self.record.get("id")
        if isinstance(rec_id, int):
            self.open_requested.emit(rec_id)


class SummaryViewerWidget(QWidget):
    """
    Widget to display a daily or weekly summary in a read-only view.
    """

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
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(20, 12, 20, 0)
        outer_layout.setSpacing(8)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(8)
        top_bar.addStretch()
        self.weekly_chat_btn = None
        if self.summary_data.get("type") == "weekly":
            self.weekly_chat_btn = QPushButton("💬 Chat This Week")
            self.weekly_chat_btn.setToolTip("Open this week's chat in a floating window")
            self.weekly_chat_btn.setProperty("class", "calendar-primary-btn")
            self.weekly_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.weekly_chat_btn.setMinimumHeight(38)
            self.weekly_chat_btn.setMinimumWidth(180)
            self.weekly_chat_btn.clicked.connect(self._open_week_chat)
            top_bar.addWidget(self.weekly_chat_btn, 0, Qt.AlignmentFlag.AlignRight)
        outer_layout.addLayout(top_bar)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer_layout.addWidget(scroll)

        page = QWidget()
        scroll.setWidget(page)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 20)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        type_ = self.summary_data.get("type", "daily")
        if type_ == "daily":
            title_text = f"📅 Daily Summary - {self.summary_data.get('date')}"
        else:
            title_text = f"Week Summary - Week of {self.summary_data.get('week_start')}"

        title = QLabel(title_text)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Metadata
        meta_layout = QHBoxLayout()
        generated_at = self.summary_data.get("generated_at", "Unknown")
        self.meta_label = QLabel(f"Generated at: {generated_at}")
        self.meta_label.setStyleSheet("color: #777; font-size: 12px;")
        meta_layout.addWidget(self.meta_label)
        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        # For daily summaries, expose tabs.
        if self.summary_data.get("type") == "daily":
            self._build_daily_tabs(layout)
        else:
            self._build_weekly_overview(layout)

        # Actions
        actions_layout = QHBoxLayout()
        type_str = self.summary_data.get("type", "daily")

        if type_str == "daily":
            regenerate_btn = QPushButton("↻ Regenerate Daily Summary")
            regenerate_btn.setToolTip("Regenerate this daily summary (will check for new recordings)")
            self._style_action_button(regenerate_btn)
            regenerate_btn.clicked.connect(lambda: self.regenerate_requested.emit(self.summary_data))
            actions_layout.addWidget(regenerate_btn)

            actions_layout.addStretch()

            chat_btn = QPushButton("💬 Chat this day")
            chat_btn.setToolTip("Open a chat filtered to this day")
            self._style_action_button(chat_btn)
            chat_btn.clicked.connect(self._open_day_chat)
            actions_layout.addWidget(chat_btn)
        else:
            actions_layout.addStretch()
        layout.addLayout(actions_layout)

    def _build_daily_tabs(self, root_layout):
        self.summary_tabs = QTabWidget()

        # General tab: only the main summary block.
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setContentsMargins(0, 0, 0, 0)
        general_layout.setSpacing(8)

        self.content_area = AutoSizingMarkdownView()
        self.content_area.setMarkdown(self.summary_data.get("summary", ""))
        self.content_area.setStyleSheet(
            "font-size: 14px; line-height: 1.7;"
            "background: transparent; border: none; padding: 0;"
        )
        general_layout.addWidget(self.content_area)
        self.summary_tabs.addTab(general_tab, "General")

        date_ref = self.summary_data.get("date")
        tags_filter = self.summary_data.get("tags_filter")

        self.daily_created_board = TasksListWidget(
            self.db,
            show_controls=False,
            snapshot_mode="day_created",
            snapshot_ref=date_ref,
            parent=self,
        )
        self.daily_created_board.global_tags_filter = tags_filter
        self.daily_created_board.open_recording_requested.connect(self.open_recording_requested.emit)
        self.summary_tabs.addTab(self.daily_created_board, "Created Today")

        self.daily_completed_board = TasksListWidget(
            self.db,
            show_controls=False,
            snapshot_mode="day_completed",
            snapshot_ref=date_ref,
            parent=self,
        )
        self.daily_completed_board.global_tags_filter = tags_filter
        self.daily_completed_board.open_recording_requested.connect(self.open_recording_requested.emit)
        self.summary_tabs.addTab(self.daily_completed_board, "Completed Today")

        root_layout.addWidget(self.summary_tabs, 1)
        self._refresh_daily_task_boards()

    def _build_weekly_tasks_snapshot(self, root_layout):
        if not self.db:
            return
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)

        header_row = QHBoxLayout()
        title = QLabel("Weekly Tasks Snapshot")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_row.addWidget(title)
        header_row.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "calendar-nav-btn")
        refresh_btn.clicked.connect(self._load_weekly_tasks_snapshot)
        header_row.addWidget(refresh_btn)
        container_layout.addLayout(header_row)

        lists_row = QHBoxLayout()
        lists_row.setSpacing(12)
        self.weekly_task_boards = {}
        sections = [
            ("week_created", "Created This Week"),
            ("week_completed", "Completed This Week"),
            ("week_pending_before", "Pending From Before"),
        ]
        week_ref = self.summary_data.get("week_start")
        tags_filter = self.summary_data.get("tags_filter")
        for mode, label in sections:
            col = QVBoxLayout()
            title_lbl = QLabel(label)
            title_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
            col.addWidget(title_lbl)
            board = TasksListWidget(
                self.db,
                show_controls=False,
                snapshot_mode=mode,
                snapshot_ref=week_ref,
                parent=self,
            )
            board.global_tags_filter = tags_filter
            board.open_recording_requested.connect(self.open_recording_requested.emit)
            col.addWidget(board, 1)
            host = QWidget()
            host.setLayout(col)
            lists_row.addWidget(host, 1)
            self.weekly_task_boards[mode] = (title_lbl, board, label)

        container_layout.addLayout(lists_row, 1)
        root_layout.addWidget(container, 2)
        self._load_weekly_tasks_snapshot()

    def _build_weekly_overview(self, root_layout):
        summary_card = QFrame()
        summary_card.setObjectName("weeklySummaryCard")
        summary_card.setStyleSheet(
            "QFrame#weeklySummaryCard {"
            "background-color: rgba(127, 127, 127, 0.06);"
            "border: 1px solid rgba(127, 127, 127, 0.22);"
            "border-radius: 18px;"
            "}"
        )
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(22, 20, 22, 20)
        summary_layout.setSpacing(10)

        eyebrow = QLabel("Weekly Narrative")
        eyebrow.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 0.08em; color: palette(highlight);")
        summary_layout.addWidget(eyebrow)

        hero_title = QLabel("What mattered this week")
        hero_title.setStyleSheet("font-size: 26px; font-weight: 800;")
        summary_layout.addWidget(hero_title)

        hero_subtitle = QLabel("A focused digest of progress, decisions, and follow-up work.")
        hero_subtitle.setStyleSheet("font-size: 13px; color: palette(mid);")
        summary_layout.addWidget(hero_subtitle)

        self.content_area = AutoSizingMarkdownView()
        self.content_area.setMarkdown(self.summary_data.get("summary", ""))
        self.content_area.setStyleSheet(
            "font-size: 15px; line-height: 1.8;"
            "background-color: rgba(127, 127, 127, 0.04);"
            "border: 1px solid rgba(127, 127, 127, 0.16);"
            "border-radius: 14px;"
            "padding: 10px 12px;"
        )
        summary_layout.addWidget(self.content_area)
        root_layout.addWidget(summary_card, 3)

        tasks_panel = QWidget()
        tasks_layout = QVBoxLayout(tasks_panel)
        tasks_layout.setContentsMargins(0, 0, 0, 0)
        tasks_layout.setSpacing(10)
        tasks_title = QLabel("Tasks")
        tasks_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        tasks_layout.addWidget(tasks_title)
        self._build_weekly_task_tabs(tasks_layout)
        root_layout.addWidget(tasks_panel, 2)

        recordings_panel = QWidget()
        recordings_layout = QVBoxLayout(recordings_panel)
        recordings_layout.setContentsMargins(0, 0, 0, 0)
        recordings_layout.setSpacing(10)
        recordings_title = QLabel("Recordings This Week")
        recordings_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        recordings_layout.addWidget(recordings_title)

        self.weekly_recordings_meta = QLabel("")
        self.weekly_recordings_meta.setStyleSheet("font-size: 12px; color: palette(mid);")
        recordings_layout.addWidget(self.weekly_recordings_meta)

        self.weekly_recordings_list = QListWidget()
        self.weekly_recordings_list.setProperty("class", "embedded-list")
        self.weekly_recordings_list.setSpacing(8)
        self.weekly_recordings_list.setAlternatingRowColors(False)
        self.weekly_recordings_list.setMinimumHeight(420)
        self.weekly_recordings_list.setStyleSheet(
            "QListWidget {"
            "background-color: rgba(127, 127, 127, 0.04);"
            "border: 1px solid rgba(127, 127, 127, 0.16);"
            "border-radius: 16px;"
            "padding: 8px;"
            "}"
            "QListWidget::item {"
            "border: none;"
            "padding: 4px 0px;"
            "background: transparent;"
            "}"
            "QListWidget::item:selected {"
            "background: transparent;"
            "}"
        )
        recordings_layout.addWidget(self.weekly_recordings_list, 1)
        root_layout.addWidget(recordings_panel, 2)
        self._load_weekly_tasks_snapshot()
        self._load_weekly_recordings()

    def _build_weekly_task_tabs(self, root_layout):
        self.weekly_tasks_tabs = QTabWidget()
        self.weekly_task_boards = {}
        sections = [
            ("week_created", "Created"),
            ("week_completed", "Completed"),
            ("week_pending_before", "Pending From Before"),
        ]
        week_ref = self.summary_data.get("week_start")
        tags_filter = self.summary_data.get("tags_filter")
        for mode, label in sections:
            board = TasksListWidget(
                self.db,
                show_controls=False,
                snapshot_mode=mode,
                snapshot_ref=week_ref,
                parent=self,
            )
            board.global_tags_filter = tags_filter
            board.setMinimumHeight(360)
            board.open_recording_requested.connect(self.open_recording_requested.emit)
            self.weekly_tasks_tabs.addTab(board, label)
            self.weekly_task_boards[mode] = board
        self.weekly_tasks_tabs.setMinimumHeight(420)
        root_layout.addWidget(self.weekly_tasks_tabs, 1)

    def _load_weekly_tasks_snapshot(self):
        if not hasattr(self, "weekly_task_boards"):
            return
        week_start = self.summary_data.get("week_start")
        tags_filter = self.summary_data.get("tags_filter")
        snapshot = self.db.get_weekly_task_snapshot(week_start, tags_filter) if (self.db and week_start) else {}
        mapping = {
            "week_created": "created_this_week",
            "week_completed": "completed_this_week",
            "week_pending_before": "pending_from_before",
        }
        title_map = {
            "week_created": "Created",
            "week_completed": "Completed",
            "week_pending_before": "Pending From Before",
        }
        for mode, board in self.weekly_task_boards.items():
            key = mapping.get(mode, "")
            board.snapshot_ref = week_start
            board.global_tags_filter = tags_filter
            board.refresh()
            if hasattr(self, "weekly_tasks_tabs"):
                idx = self.weekly_tasks_tabs.indexOf(board)
                if idx >= 0:
                    self.weekly_tasks_tabs.setTabText(idx, f"{title_map.get(mode, mode)} ({len(snapshot.get(key, []))})")

    def _load_weekly_recordings(self):
        if not self.db or not hasattr(self, "weekly_recordings_list"):
            return
        start, end = self._get_batch_range()
        if not start:
            return
        tags = self._get_summary_tags()
        records = self.db.fetch_by_date_range(start, end, tags=tags)
        self.weekly_recordings_list.clear()
        self.weekly_recordings_meta.setText(f"{len(records)} recording(s) in scope")
        if not records:
            item = QListWidgetItem("No recordings found for this week.")
            self.weekly_recordings_list.addItem(item)
            return
        for rec in records:
            item = QListWidgetItem()
            row = WeeklyRecordingRowWidget(rec, self)
            row.open_requested.connect(self.open_recording_requested.emit)
            item.setSizeHint(row.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, rec)
            self.weekly_recordings_list.addItem(item)
            self.weekly_recordings_list.setItemWidget(item, row)

    def _refresh_daily_task_boards(self):
        date_ref = self.summary_data.get("date")
        tags_filter = self.summary_data.get("tags_filter")
        if hasattr(self, "daily_created_board"):
            self.daily_created_board.snapshot_ref = date_ref
            self.daily_created_board.global_tags_filter = tags_filter
            self.daily_created_board.refresh()
        if hasattr(self, "daily_completed_board"):
            self.daily_completed_board.snapshot_ref = date_ref
            self.daily_completed_board.global_tags_filter = tags_filter
            self.daily_completed_board.refresh()

    def _get_summary_tags(self):
        tags_filter = self.summary_data.get("tags_filter")
        if not tags_filter:
            return None
        return [t.strip() for t in str(tags_filter).split(",") if t.strip()]

    def _open_day_chat(self):
        date_str = self.summary_data.get("date")
        if date_str:
            self.start_chat_requested.emit(date_str, [])

    def _open_week_chat(self):
        start, end = self._get_batch_range()
        if not start or not end:
            return
        contexts = [
            {
                "type": "date_range",
                "value": {"start": start, "end": end},
                "label": f"{start} to {end}",
            }
        ]
        for tag in self._get_summary_tags() or []:
            contexts.append({"type": "tag", "value": tag, "label": tag})
        if self.db:
            for rec in self.db.fetch_by_date_range(start, end, tags=self._get_summary_tags()):
                rec_id = rec.get("id")
                if isinstance(rec_id, int):
                    contexts.append(
                        {
                            "type": "recording",
                            "value": rec_id,
                            "label": (rec.get("title") or f"Recording {rec_id}").strip(),
                        }
                    )
        self.start_chat_contexts_requested.emit(contexts, True)

    def _style_action_button(self, button):
        button.setProperty("class", "calendar-nav-btn")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(34)

    def _get_batch_range(self):
        type_str = self.summary_data.get("type", "daily")
        if type_str == "daily":
            date_str = self.summary_data.get("date")
            return date_str, date_str
        else:
            # Weekly - week_start is the Sunday anchor
            sunday_str = self.summary_data.get("week_start")
            if not sunday_str: return None, None
            sunday = QDate.fromString(sunday_str, "yyyy-MM-dd")
            monday = sunday.addDays(-6)
            return monday.toString("yyyy-MM-dd"), sunday_str

    def update_content(self, summary_data):
        """Update the content of the viewer with new data."""
        self.summary_data = summary_data
        self.content_area.setMarkdown(self.summary_data.get("summary", ""))

        generated_at = self.summary_data.get("generated_at", "Unknown")
        self.meta_label.setText(f"Generated at: {generated_at}")

        if self.summary_data.get("type") == "daily":
            self._refresh_daily_task_boards()
        else:
            self._load_weekly_tasks_snapshot()
            self._load_weekly_recordings()
