from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QInputDialog,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from src.ui.components import TaskRowWidget
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
            layout.addWidget(self.content_area)

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

        # Tasks tab - using unified component
        self.tasks_board = TasksListWidget(
            self.db, 
            filter_date=self.summary_data.get("date"),
            parent=self
        )
        self.tasks_board.open_recording_requested.connect(self.open_recording_requested.emit)
        self.summary_tabs.addTab(self.tasks_board, "Day Tasks")

        root_layout.addWidget(self.summary_tabs, 3)
        self._build_daily_columns(root_layout)

        self._load_daily_recordings()

    def _build_daily_columns(self, layout):
        self.daily_split_layout = QHBoxLayout()
        self.daily_split_layout.setSpacing(16)

        left_col = QVBoxLayout()
        self.daily_recordings_title = QLabel("Recordings")
        self.daily_recordings_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        left_col.addWidget(self.daily_recordings_title)

        self.daily_recordings_list = QListWidget()
        self.daily_recordings_list.setProperty("class", "embedded-list")
        self.daily_recordings_list.itemClicked.connect(self._on_daily_recording_clicked)
        left_col.addWidget(self.daily_recordings_list)

        left_col_host = QWidget()
        left_col_host.setLayout(left_col)
        left_col_host.setMaximumWidth(420)
        self.daily_split_layout.addWidget(left_col_host, 1)

        right_col = QVBoxLayout()
        self.daily_tags_title = QLabel("Tags")
        self.daily_tags_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        right_col.addWidget(self.daily_tags_title)

        self.daily_tags_list = QListWidget()
        self.daily_tags_list.setProperty("class", "embedded-list")
        self.daily_tags_list.itemClicked.connect(self._on_daily_tag_clicked)
        right_col.addWidget(self.daily_tags_list)

        right_col_host = QWidget()
        right_col_host.setLayout(right_col)
        self.daily_split_layout.addWidget(right_col_host, 2)

        layout.addLayout(self.daily_split_layout, 2)

    def _get_summary_tags(self):
        tags_filter = self.summary_data.get("tags_filter")
        if not tags_filter:
            return None
        return [t.strip() for t in str(tags_filter).split(",") if t.strip()]

    def _load_daily_recordings(self):
        if not self.db or not hasattr(self, "daily_recordings_list"):
            return

        date = self.summary_data.get("date")
        if not date:
            return

        tags = self._get_summary_tags()
        records = self.db.fetch_by_date_range(date, date, tags=tags)

        self.daily_recordings_list.clear()
        self.daily_recordings_title.setText(f"Recordings ({len(records)})")

        if not records:
            self.daily_recordings_list.addItem("No recordings found for this day.")
            self.daily_tags_title.setText("Tags (0)")
            self.daily_tags_list.clear()
            self.daily_tags_list.addItem("No tags found for this day.")
            return

        for record in records:
            title = record.get("title") or f"Recording {record.get('id')}"
            created_at = record.get("created_at", "")
            time_part = created_at[11:16] if len(created_at) >= 16 else ""
            line = f"{time_part}  {title}" if time_part else title
            item = QListWidgetItem(line)
            item.setData(Qt.ItemDataRole.UserRole, record.get("id"))
            self.daily_recordings_list.addItem(item)

        self._update_daily_tags_summary(records)

    def _update_daily_tags_summary(self, records):
        tag_counts = {}

        for record in records:
            raw_tags = record.get("tags") or ""
            tags = [t.strip() for t in str(raw_tags).split(",") if t.strip()]
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        sorted_tags = sorted(tag_counts.items(), key=lambda pair: (-pair[1], pair[0].lower()))
        self.daily_tags_title.setText(f"Tags ({len(sorted_tags)})")
        self.daily_tags_list.clear()
        if not sorted_tags:
            self.daily_tags_list.addItem("No tags on this day.")
            return
        for tag, count in sorted_tags:
            item = QListWidgetItem(f"{tag} ({count})")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.daily_tags_list.addItem(item)

    def _on_daily_tag_clicked(self, item):
        date_str = self.summary_data.get("date")
        tag = item.data(Qt.ItemDataRole.UserRole)
        if date_str and isinstance(tag, str) and tag.strip():
            self.start_chat_requested.emit(date_str, [tag.strip()])

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
            if rec.get('transcription'):
                if self.task_queue.enqueue_task_extraction(
                    rec['id'], 
                    rec['transcription'], 
                    rec.get('tags', '') or '',
                    rec.get('title') or f"Recording {rec['id']}"
                ):
                    enqueued += 1
        
        QMessageBox.information(
            self,
            "Encolado",
            f"Se han encolado {enqueued} extracciones de tareas, una por grabación."
        )

    def _on_daily_recording_clicked(self, item):
        record_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(record_id, int):
            self.open_recording_requested.emit(record_id)

    def update_content(self, summary_data):
        """Update the content of the viewer with new data."""
        self.summary_data = summary_data
        self.content_area.setMarkdown(self.summary_data.get("summary", ""))

        generated_at = self.summary_data.get("generated_at", "Unknown")
        self.meta_label.setText(f"Generated at: {generated_at}")

        if self.summary_data.get("type") == "daily":
            self._load_daily_recordings()
            if hasattr(self, "tasks_board"):
                self.tasks_board.filter_date = self.summary_data.get("date")
                self.tasks_board.refresh()
