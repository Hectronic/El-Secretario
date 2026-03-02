import os

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from src.ui.tasks_list_widget import TasksListWidget


class SummaryViewerWidget(QWidget):
    """
    Widget to display a daily or weekly summary in a read-only view.
    """

    close_requested = pyqtSignal()
    regenerate_requested = pyqtSignal(dict)
    open_recording_requested = pyqtSignal(int)
    start_chat_requested = pyqtSignal(str, list)

    def __init__(self, summary_data, db=None, task_queue=None, parent=None):
        super().__init__(parent)
        self.summary_data = summary_data
        self.db = db
        self.task_queue = task_queue
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
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
            self.content_area = QTextEdit()
            self.content_area.setReadOnly(True)
            self.content_area.setMarkdown(self.summary_data.get("summary", ""))
            self.content_area.setStyleSheet("font-size: 14px; line-height: 1.6;")
            layout.addWidget(self.content_area, 2)
            self._build_weekly_tasks_snapshot(layout)

        # Actions
        actions_layout = QHBoxLayout()
        
        type_str = self.summary_data.get("type", "daily")
        context_label = "day" if type_str == "daily" else "week"

        reprocess_btn = QPushButton(f"🔄 Re-process {context_label} (Whisper + AI)")
        reprocess_btn.setToolTip(f"Re-transcribe and summarize all recordings in this {context_label}")
        self._style_action_button(reprocess_btn)
        reprocess_btn.clicked.connect(self._reprocess_batch)
        actions_layout.addWidget(reprocess_btn)
        
        extract_tasks_btn = QPushButton(f"✅ Extract tasks {context_label} (AI)")
        extract_tasks_btn.setToolTip(f"Extract tasks from all recordings in this {context_label}")
        self._style_action_button(extract_tasks_btn)
        extract_tasks_btn.clicked.connect(self._extract_tasks_batch)
        actions_layout.addWidget(extract_tasks_btn)

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

        self.content_area = QTextEdit()
        self.content_area.setReadOnly(True)
        self.content_area.setMarkdown(self.summary_data.get("summary", ""))
        self.content_area.setStyleSheet("font-size: 14px; line-height: 1.6;")
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
        for mode, (title_lbl, board, base_label) in self.weekly_task_boards.items():
            key = mapping.get(mode, "")
            title_lbl.setText(f"{base_label} ({len(snapshot.get(key, []))})")
            board.snapshot_ref = week_start
            board.global_tags_filter = tags_filter
            board.refresh()

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

    def _reprocess_batch(self):
        if not self.task_queue: return
        start, end = self._get_batch_range()
        if not start: return
        
        records = self.db.fetch_by_date_range(start, end)
        if not records:
            QMessageBox.information(self, "Info", "No hay grabaciones en este periodo.")
            return
            
        type_label = "día" if self.summary_data.get("type") == "daily" else "semana"
        reply = QMessageBox.question(self, "Confirmar Re-procesamiento", 
                                   f"Esto re-transcribirá y resumirá {len(records)} grabaciones de este {type_label}. ¿Continuar?")
        if reply != QMessageBox.StandardButton.Yes: return
        
        # Enqueue all
        from PyQt6.QtCore import QSettings
        settings = QSettings("Hectronic", "Secretario")
        model_size = settings.value("whisper_model", "base")
        
        for rec in records:
            audio_path = os.path.join(os.getcwd(), "recordings", rec['filename'])
            if os.path.exists(audio_path):
                # transcription -> summary -> task_extraction (chained)
                self.task_queue.enqueue_transcription(
                    rec['id'], 
                    audio_path, 
                    model_size=model_size,
                    title=rec.get('title') or f"Recording {rec['id']}"
                )
        
        QMessageBox.information(self, "Encolado", f"Se han encolado {len(records)} grabaciones para procesar.")

    def _extract_tasks_batch(self):
        if not self.task_queue: return
        start, end = self._get_batch_range()
        if not start: return
        
        tags = self._get_summary_tags()
        records = self.db.fetch_by_date_range(start, end, tags=tags)
        if not records:
            QMessageBox.information(self, "Info", "No hay grabaciones en este periodo.")
            return
            
        type_label = "día" if self.summary_data.get("type") == "daily" else "semana"
        reply = QMessageBox.question(self, "Confirmar Extracción", 
                                   f"Esto extraerá tareas de {len(records)} grabaciones de este {type_label}. ¿Continuar?")
        if reply != QMessageBox.StandardButton.Yes: return
        
        enqueued = 0
        for rec in records:
            ai_text = self.db.compose_ai_text(rec.get('transcription', ''), rec.get('recording_notes', ''))
            if ai_text:
                if self.task_queue.enqueue_task_extraction(
                    rec['id'], 
                    ai_text, 
                    rec.get('tags', '') or '',
                    rec.get('title') or f"Recording {rec['id']}"
                ):
                    enqueued += 1
        
        QMessageBox.information(
            self,
            "Encolado",
            f"Se han encolado {enqueued} extracciones de tareas, una por grabación."
        )

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
