# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import re
import shutil
import logging
from datetime import date, timedelta
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QPushButton, QToolButton,
                             QLabel, QMessageBox, QListWidgetItem, QComboBox, QInputDialog,
                             QTabWidget, QSplitter, QApplication, QStyle, QLineEdit, QTabBar,
                             QCalendarWidget, QCheckBox, QFileDialog, QMenu, QProgressBar, QDialog,
                             QFrame)
from PyQt6.QtCore import Qt, QSettings, QUrl, QDate, QTimer, QPoint, QEvent, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QDesktopServices, QTextCharFormat, QColor, QCursor

from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.worker import SearchThread
from src.ui.dialogs import SettingsWidget, SpeakerDialog
from src.ui.welcome_widget import WelcomeWidget
from src.ui.recording_widget import RecordingWidget
from src.ui.audio_editor_widget import AudioEditorWidget
from src.ui.recording_in_progress_widget import RecordingInProgressWidget
from src.ui.search_results_widget import SearchResultsWidget
from src.ui.chat_widget import ChatWidget
from src.ui.chat_widget import ContextManagerPanel
from src.ui.collection_widget import CollectionWidget
from src.ui.calendar_widget import CalendarWidget
from src.ui.styles import LIST_WIDGET_STYLE, NEW_CHAT_BUTTON_STYLE, apply_theme
from src.ui.components import (
    RecordingListItemWidget,
    SummaryListItemWidget,
    SidebarChatSessionWidget,
    SidebarTaskCompactWidget,
)

from src.ui.batch_process_widget import BatchProcessWidget
from src.ui.summary_viewer import SummaryViewerWidget
from src.notebook_database import NotebookDBManager
from src.ui.notebooks_list_widget import NotebooksListWidget
from src.ui.notebook_widget import NotebookWidget
from src.ui.note_widget import NoteWidget
from src.ui.maintenance_widget import MaintenanceWidget
from src.ui.tools_widget import ToolsWidget
from src.ui.summary_task_queue import SummaryTaskQueueManager
from src.ui.queue_management_widget import QueueManagementWidget
from src.ui.chat_history_widget import ChatHistoryWidget
from src.ui.tasks_list_widget import TasksListWidget, TaskEditDialog

Recorder = None


class FloatingChatHost(QFrame):
    size_changed = pyqtSignal()

    DEFAULT_WIDTH = 420
    DEFAULT_HEIGHT = 380
    MIN_WIDTH = 320
    MIN_HEIGHT = 260
    MAX_WIDTH = 760
    MAX_HEIGHT = 680
    MINIMIZED_WIDTH = 260
    MINIMIZED_HEIGHT = 32
    RESIZE_HANDLE_SIZE = 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preferred_size = QSize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self._min_size = QSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self._max_size = QSize(self.MAX_WIDTH, self.MAX_HEIGHT)
        self._resize_enabled = True
        self._resizing = False
        self._drag_origin = QPoint()
        self._start_size = QSize(self._preferred_size)
        self.setMouseTracking(True)
        self.resize_handle = QLabel(self)
        self.resize_handle.setObjectName("floatingChatResizeHandle")
        self.resize_handle.setFixedSize(self.RESIZE_HANDLE_SIZE, self.RESIZE_HANDLE_SIZE)
        self.resize_handle.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.resize_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resize_handle.setToolTip("Drag to resize")
        self.resize_handle.setMouseTracking(True)
        self.resize_handle.installEventFilter(self)
        self.resize_handle.raise_()

    def sizeHint(self):
        return QSize(self._preferred_size)

    def minimumSizeHint(self):
        return QSize(self.minimumWidth(), self.minimumHeight())

    def set_preferred_size(self, size: QSize):
        bounded = QSize(
            max(self._min_size.width(), min(size.width(), self._max_size.width())),
            max(self._min_size.height(), min(size.height(), self._max_size.height())),
        )
        self._preferred_size = bounded
        self.setFixedSize(bounded)
        self.updateGeometry()
        self.size_changed.emit()

    def set_size_bounds(self, min_size: QSize, max_size: QSize):
        self._min_size = QSize(min_size)
        self._max_size = QSize(max_size)

    def set_resize_enabled(self, enabled: bool):
        self._resize_enabled = bool(enabled)
        self.resize_handle.setVisible(self._resize_enabled)
        if not self._resize_enabled and not self._resizing:
            self.unsetCursor()

    def _position_resize_handle(self):
        margin = 3
        x = margin
        y = margin
        self.resize_handle.move(x, y)

    def _in_resize_zone(self, pos):
        return (
            self._resize_enabled
            and pos.x() <= self.RESIZE_HANDLE_SIZE
            and pos.y() <= self.RESIZE_HANDLE_SIZE
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._in_resize_zone(event.position().toPoint()):
            self._resizing = True
            self._drag_origin = event.globalPosition().toPoint()
            self._start_size = QSize(self._preferred_size)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = self._drag_origin - event.globalPosition().toPoint()
            self.set_preferred_size(
                QSize(
                    self._start_size.width() + delta.x(),
                    self._start_size.height() + delta.y(),
                )
            )
            event.accept()
            return
        if self._in_resize_zone(event.position().toPoint()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing and event.button() == Qt.MouseButton.LeftButton:
            self._resizing = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        if not self._resizing:
            self.unsetCursor()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        self._position_resize_handle()
        super().resizeEvent(event)

    def eventFilter(self, watched, event):
        if watched is self.resize_handle:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._resizing = True
                self._drag_origin = event.globalPosition().toPoint()
                self._start_size = QSize(self._preferred_size)
                self.resize_handle.grabMouse(Qt.CursorShape.SizeFDiagCursor)
                return True
            if event.type() == QEvent.Type.MouseMove and self._resizing:
                delta = self._drag_origin - event.globalPosition().toPoint()
                self.set_preferred_size(
                    QSize(
                        self._start_size.width() + delta.x(),
                        self._start_size.height() + delta.y(),
                    )
                )
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and self._resizing:
                self._resizing = False
                self.resize_handle.releaseMouse()
                return True
        return super().eventFilter(watched, event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        import logging
        logging.info("Initializing MainWindow...")
        self.setWindowTitle("El Secretario")
        self.setWindowIcon(QIcon("logo.png"))
        self.resize(1450, 860)

        self.db = DBManager()
        self.notebook_db = NotebookDBManager()
        global Recorder
        if Recorder is None:
            from src.audio import Recorder as _Recorder
            Recorder = _Recorder
        self.recorder = Recorder()
        # We can connect global recorder signals here if needed, 
        # but RecordingWidget handles its own UI updates.
        
        self.search_thread = None
        self.regen_worker = None
        self.summary_task_queue = SummaryTaskQueueManager(self)
        self.tasks_sidebar_limit = 20
        self._pending_history_reload = False
        self._pending_tag_reload = False
        self._sidebar_refresh_timer = QTimer(self)
        self._sidebar_refresh_timer.setSingleShot(True)
        self._sidebar_refresh_timer.timeout.connect(self._apply_pending_sidebar_reload)
        self._right_sidebar_sections = {}
        self._active_right_section = None
        self._right_sidebar_layout = None
        self._right_sidebar_bottom_spacer_index = None
        self._right_sidebar_last_non_chat_section = "tasks"
        self.floating_chat_hosts = []
        
        apply_theme()
        
        self.init_ui()
        self._log_user_settings_snapshot("startup")
        self.load_history()
        self.refresh_tag_filter()
        self.load_chat_sessions()
        self.refresh_tasks_sidebar()
        self.load_notebooks()
        self._setup_task_status_bar()
        self._connect_task_queue_signals()
        self._enqueue_missing_previous_week_summary_if_enabled()
        self._enqueue_missing_previous_daily_summary_if_enabled()
        
        # Show Welcome Tab
        self.show_welcome_screen()
        logging.info("MainWindow initialized.")

    @staticmethod
    def _to_env_bool(value) -> str:
        return "1" if bool(value) else "0"

    def _apply_rag_runtime_env(self, rag_config):
        os.environ["EL_SECRETARIO_CHROMA_SAFE_DELETE"] = self._to_env_bool(
            rag_config.get("safe_delete_mode", True)
        )
        os.environ["EL_SECRETARIO_RAG_SUBPROCESS_UPSERT"] = self._to_env_bool(
            rag_config.get("subprocess_upsert_mode", True)
        )
        os.environ["EL_SECRETARIO_RAG_SUBPROCESS_QUERY"] = self._to_env_bool(
            rag_config.get("subprocess_query_mode", True)
        )

    def _propagate_rag_engine_to_open_tabs(self):
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if hasattr(widget, "rag"):
                try:
                    widget.rag = self.rag
                except Exception:
                    logging.exception("Failed to propagate RAG engine to tab %s", type(widget).__name__)

    def _build_rag_engine(self, rag_config, reason="runtime"):
        self._apply_rag_runtime_env(rag_config)
        if not rag_config.get("enabled", True):
            self.rag = None
            self.summary_task_queue.set_rag_engine(None)
            self._propagate_rag_engine_to_open_tabs()
            self.handle_status_message("RAG disabled from settings.")
            logging.info("RAG disabled (%s).", reason)
            return

        persist_dir = rag_config.get("persist_directory") or "chroma_db"
        try:
            from src.rag_engine import RAGEngine
            self.rag = RAGEngine(persist_directory=persist_dir)
            self.summary_task_queue.set_rag_engine(self.rag)
            self._propagate_rag_engine_to_open_tabs()
            self.handle_status_message(f"RAG ready ({reason}).")
            logging.info("RAG initialized (%s) with persist_directory=%s", reason, persist_dir)
        except Exception as e:
            self.rag = None
            self.summary_task_queue.set_rag_engine(None)
            self._propagate_rag_engine_to_open_tabs()
            logging.exception("Failed to initialize RAG (%s).", reason)
            if str(reason).lower() == "startup":
                self.handle_status_message(f"RAG unavailable on startup: {e}")
            else:
                QMessageBox.warning(self, "RAG Error", f"Failed to initialize RAG: {e}")

    def _log_user_settings_snapshot(self, context: str):
        settings = QSettings("Hectronic", "Secretario")
        snapshot = {}
        for key in sorted(settings.allKeys()):
            value = settings.value(key)
            key_l = str(key).lower()
            if any(token in key_l for token in ("token", "password", "secret", "apikey", "api_key")):
                snapshot[key] = "***"
            else:
                snapshot[key] = value
        logging.info("User settings snapshot [%s]: %s", context, snapshot)

    def _enqueue_missing_previous_week_summary_if_enabled(self):
        settings = QSettings("Hectronic", "Secretario")
        if not settings.value("startup_enqueue_last_weekly_summary", False, type=bool):
            return

        today = date.today()
        current_week_monday = today - timedelta(days=today.weekday())
        previous_week_monday = current_week_monday - timedelta(days=7)
        previous_week_sunday = previous_week_monday + timedelta(days=6)
        week_sunday_str = previous_week_sunday.isoformat()

        existing = self.db.get_weekly_summary(week_sunday_str, tags_filter=None)
        if existing:
            return

        start_str = previous_week_monday.isoformat()
        end_str = previous_week_sunday.isoformat()
        records = self.db.fetch_by_date_range(start_str, end_str, tags=None, favorites_only=False)
        if not records:
            return

        full_text = ""
        for rec in records:
            title = rec.get("title") or "Untitled"
            created_at = rec.get("created_at") or ""
            composed = self.db.compose_ai_text(rec.get("transcription"), rec.get("recording_notes"))
            if not composed.strip():
                continue
            full_text += f"\n\n--- Recording: {title} ({created_at}) ---\n"
            full_text += composed

        if not full_text.strip():
            return

        self.summary_task_queue.enqueue_weekly_summary(week_sunday_str, full_text, "", source="startup")

    def _enqueue_missing_previous_daily_summary_if_enabled(self):
        settings = QSettings("Hectronic", "Secretario")
        if not settings.value("startup_enqueue_previous_daily_summary", False, type=bool):
            return

        today_str = date.today().isoformat()
        target_day = self.db.get_latest_recording_day_without_daily_summary(today_str, tags_filter=None)
        if not target_day:
            return

        self.summary_task_queue.enqueue_daily_summary(
            {
                "date": target_day,
                "tags_filter": "",
                "source": "startup",
            }
        )

    def _setup_task_status_bar(self):
        status = self.statusBar()
        self.task_status_label = QLabel("Summary queue idle.")
        self.task_status_label.setStyleSheet("padding-right: 8px;")
        
        self.open_queue_btn = QPushButton("📋 View Queue")
        self.open_queue_btn.setFlat(True)
        self.open_queue_btn.setStyleSheet("color: #2196F3; text-decoration: underline; font-weight: bold;")
        self.open_queue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_queue_btn.clicked.connect(self.open_queue_manager_tab)
        
        self.task_queue_progress = QProgressBar()
        self.task_queue_progress.setFixedWidth(180)
        self.task_queue_progress.setTextVisible(False)
        self.task_queue_progress.setRange(0, 1)
        self.task_queue_progress.setValue(0)
        
        status.addPermanentWidget(self.task_status_label, 1)
        status.addPermanentWidget(self.open_queue_btn)
        status.addPermanentWidget(self.task_queue_progress)

    def open_queue_manager_tab(self):
        """Open the task queue management tab."""
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, QueueManagementWidget):
                self.central_tabs.setCurrentIndex(i)
                return

        queue_widget = QueueManagementWidget(self.summary_task_queue)
        index = self.central_tabs.addTab(queue_widget, "📋 Task Queue")
        self.central_tabs.setCurrentIndex(index)

    def _connect_task_queue_signals(self):
        self.summary_task_queue.task_enqueued.connect(self._on_summary_task_enqueued)
        self.summary_task_queue.task_started.connect(self._on_summary_task_started)
        self.summary_task_queue.task_finished.connect(self._on_summary_task_finished)
        self.summary_task_queue.task_failed.connect(self._on_summary_task_failed)
        self.summary_task_queue.task_skipped.connect(self._on_summary_task_skipped)
        self.summary_task_queue.queue_changed.connect(self._on_summary_queue_changed)
        self.summary_task_queue.task_progress.connect(self.handle_progress)
        self.summary_task_queue.task_status_update.connect(self.handle_status_message)

    def _format_task_name(self, task):
        t_type = task.get("type")
        if t_type == "summary":
            return f"Recording: {task.get('title', 'Unknown')}"
        if t_type == "task_extraction":
            return f"Tasks: {task.get('title', 'Unknown')}"
        if t_type == "transcription":
            return f"Transcribing: {task.get('title', 'Unknown')}"
        if t_type == "weekly_summary":
            return f"Week: {task.get('date', 'Unknown')}"
        if t_type == "rag_reindex":
            scope = task.get("reindex_scope", "all")
            if scope == "missing":
                return "RAG Reindex (Missing)"
            return "RAG Reindex (All)"
        
        date = task.get("date", "unknown date")
        tags_filter = task.get("tags_filter")
        if tags_filter:
            return f"Day: {date} [{tags_filter}]"
        return f"Day: {date}"

    def _on_summary_task_enqueued(self, task, position):
        self.task_status_label.setText(
            f"Queued task: {self._format_task_name(task)} (#{position} in queue)"
        )

    def _on_summary_task_started(self, task, remaining_pending):
        self.regen_worker = self.summary_task_queue.current_worker
        self.task_status_label.setText(
            f"Running: {self._format_task_name(task)} ({self.summary_task_queue.pending_count} pending)"
        )

    def _on_summary_task_finished(self, task):
        try:
            self.regen_worker = self.summary_task_queue.current_worker
            t_type = task.get("type")
            
            if t_type == "summary":
                # Update specific recording widget if open
                record_id = task.get("record_id")
                for i in range(self.central_tabs.count()):
                    widget = self.central_tabs.widget(i)
                    try:
                        if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                            widget.refresh_from_background_queue(include_summary=True)
                    except (RuntimeError, AttributeError):
                        continue # Widget might have been deleted
                self.request_sidebar_reload(include_history=True)
                
            elif t_type == "task_extraction":
                # Update specific recording widget if open
                record_id = task.get("record_id")
                for i in range(self.central_tabs.count()):
                    widget = self.central_tabs.widget(i)
                    try:
                        if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                            widget.refresh_from_background_queue(include_tasks=True)
                    except (RuntimeError, AttributeError):
                        continue
                # Also update CalendarWidget if open to show new tasks in daily view
                for i in range(self.central_tabs.count()):
                    widget = self.central_tabs.widget(i)
                    if isinstance(widget, SummaryViewerWidget):
                        widget._load_daily_tasks()
                # Keep right sidebar tasks in sync when extraction is completed by queue.
                self.refresh_tasks_sidebar()
                
            elif t_type == "daily_summary":
                date = task.get("date")
                tags_filter = task.get("tags_filter")
                if date:
                    self._refresh_daily_summary_viewers(date, tags_filter)
                    self.request_sidebar_reload(include_history=True)
                    
            elif t_type == "weekly_summary":
                self.request_sidebar_reload(include_history=True)
                # Find and update CalendarWidget if open
                for i in range(self.central_tabs.count()):
                    widget = self.central_tabs.widget(i)
                    try:
                        if isinstance(widget, CalendarWidget):
                            widget.update_summary_view()
                    except (RuntimeError, AttributeError):
                        continue
            elif t_type == "rag_reindex":
                self.request_sidebar_reload(include_history=True)

            self.task_status_label.setText(
                f"Finished: {self._format_task_name(task)}"
            )
        except Exception as e:
            import logging
            logging.error(f"Error in _on_summary_task_finished: {e}", exc_info=True)

    def _on_summary_task_failed(self, task, error_msg):
        try:
            self.regen_worker = self.summary_task_queue.current_worker
            self.task_status_label.setText(
                f"Regeneration failed for {self._format_task_name(task)}: {error_msg}"
            )
        except Exception:
            pass

    def _on_summary_task_skipped(self, task, reason):
        self.task_status_label.setText(
            f"Skipped regeneration for {self._format_task_name(task)}: {reason}"
        )

    def _on_summary_queue_changed(self, pending_count, is_running):
        self.refresh_tasks_sidebar()
        if is_running:
            self.task_queue_progress.setRange(0, 0)
            self.task_queue_progress.setVisible(True)
        else:
            self.task_queue_progress.setRange(0, 1)
            self.task_queue_progress.setValue(0 if pending_count == 0 else 1)
            if pending_count == 0:
                self.task_status_label.setText("Summary queue idle.")

    def handle_status_message(self, message):
        # During early startup, status widgets may not be created yet.
        try:
            label = self.task_status_label
        except Exception:
            label = None

        if label is None:
            try:
                self.statusBar().showMessage(str(message or ""), 5000)
            except Exception:
                pass
            return

        # If the queue is running, don't overwrite its status with generic messages
        if not self.summary_task_queue.is_running:
            label.setText(message)

    def handle_progress(self, value):
        # When the queue is running, its own state drives the global progress bar.
        if self.summary_task_queue.is_running:
            return

        if value == -1: # Indeterminate
            self.task_queue_progress.setRange(0, 0)
            self.task_queue_progress.setVisible(True)
            return
        elif value == -2: # Hide
            self.task_queue_progress.setRange(0, 1)
            self.task_queue_progress.setValue(0)
            self.task_queue_progress.setVisible(True)
            return
        else:
            self.task_queue_progress.setRange(0, 100)
            self.task_queue_progress.setValue(value)
            self.task_queue_progress.setVisible(True)

    def _refresh_daily_summary_viewers(self, date, tags_filter):
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if not isinstance(widget, SummaryViewerWidget):
                continue
            w_data = widget.summary_data
            if w_data.get("type") != "daily":
                continue
            same_date = w_data.get("date") == date
            same_tags = (w_data.get("tags_filter") or "") == (tags_filter or "")
            if not (same_date and same_tags):
                continue
            new_summary_data = self.db.get_daily_summary_details(date, tags_filter or None)
            if new_summary_data:
                new_summary_data["type"] = "daily"
                widget.update_content(new_summary_data)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- Left Panel: History & Search ---
        left_widget = QWidget()
        left_widget.setMinimumWidth(300) # Slightly wider for the custom items
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Calendar Widget
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.selectionChanged.connect(self.on_calendar_date_changed)
        # Set a fixed height or max height so it doesn't take too much space
        self.calendar.setMaximumHeight(300)
        left_layout.addWidget(self.calendar)
        
        # Week Details Button
        self.open_calendar_btn = QPushButton("Week Details")
        self.open_calendar_btn.clicked.connect(self.open_calendar_tab)
        self.open_calendar_btn.setProperty("class", "calendar-primary-btn")
        self.open_calendar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_calendar_btn.setMinimumHeight(36)
        left_layout.addWidget(self.open_calendar_btn)
        
        # Calendar Navigation
        nav_layout = QHBoxLayout()
        self.prev_week_btn = QPushButton("<< Prev Week")
        self.prev_week_btn.clicked.connect(self.prev_week_sidebar)
        self.prev_week_btn.setProperty("class", "calendar-nav-btn")
        self.prev_week_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_week_btn.setMinimumHeight(34)

        self.reset_date_btn = QPushButton("all")
        self.reset_date_btn.clicked.connect(self.reset_date_filter)
        self.reset_date_btn.setProperty("class", "calendar-nav-btn")
        self.reset_date_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_date_btn.setMinimumHeight(34)

        self.next_week_btn = QPushButton("Next Week >>")
        self.next_week_btn.clicked.connect(self.next_week_sidebar)
        self.next_week_btn.setProperty("class", "calendar-nav-btn")
        self.next_week_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_week_btn.setMinimumHeight(34)
        nav_layout.addWidget(self.prev_week_btn)
        nav_layout.addWidget(self.reset_date_btn)
        nav_layout.addWidget(self.next_week_btn)
        left_layout.addLayout(nav_layout)
        
        # Initialize date filter state
        self.current_date_filter = None # Single date (string) or None for week/all
        self.current_week_monday = None # QDate of Monday if filtering by week

        # Default view: no date filter (show all recordings at startup)
        QTimer.singleShot(100, self.update_calendar_visuals)

        # Search Box
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search recordings...")
        self.search_input.textChanged.connect(self.filter_history_list)
        search_layout.addWidget(self.search_input)
        left_layout.addLayout(search_layout)
        
        # Filter Row (Tags)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.addItem("All")
        self.tag_filter_combo.currentTextChanged.connect(self.on_tag_filter_changed)
        filter_layout.addWidget(self.tag_filter_combo)
        
        self.fav_filter_cb = QCheckBox("★")
        self.fav_filter_cb.setToolTip("Show Favorites Only")
        self.fav_filter_cb.stateChanged.connect(self.load_history)
        filter_layout.addWidget(self.fav_filter_cb)
        
        # Refresh Button
        self.refresh_btn = QPushButton()
        self.refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_btn.setToolTip("Refresh List")
        self.refresh_btn.setFixedSize(24, 24)
        self.refresh_btn.clicked.connect(self.refresh_sidebar)
        filter_layout.addWidget(self.refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        left_layout.addLayout(filter_layout)
        
        # History List
        self.history_list = QListWidget()
        # Disable horizontal scrolling - long titles will be clipped
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.history_list.setStyleSheet(LIST_WIDGET_STYLE) # Use Global Theme
        self.history_list.itemClicked.connect(self.on_history_item_clicked)
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_history_item_context_menu)
        left_layout.addWidget(self.history_list)

        self.splitter.addWidget(left_widget)

        # --- Middle Panel: Tabbed Interface ---
        self.central_tabs = QTabWidget()
        self.central_tabs.setTabsClosable(True)
        self.central_tabs.tabCloseRequested.connect(self.close_tab)
        self.central_tabs.currentChanged.connect(self._on_central_tab_changed)
        self.central_tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.central_tabs.customContextMenuRequested.connect(self.show_tab_context_menu)
        self.splitter.addWidget(self.central_tabs)
        # --- Right Panel: Accordion (Tasks, Chat History, Notebooks, Tags) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self._right_sidebar_layout = right_layout
        right_panel.setMinimumWidth(300)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(8)
        
        def create_section(section_key, title, list_widget=None, button=None, top_widget=None, header_actions=None):
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(4)

            header_shell = QWidget()
            header_shell.setProperty("class", "accordion-header-shell")
            header_shell.setStyleSheet("""
                QWidget[class="accordion-header-shell"] {
                    border: 1px solid #546E7A;
                    border-radius: 12px;
                    background-color: transparent;
                }
                QWidget[class="accordion-header-shell"][active="true"] {
                    background-color: rgba(33, 150, 243, 0.20);
                    border-color: #2196F3;
                }
                QWidget[class="accordion-header-shell"][active="false"]:hover {
                    background-color: rgba(84, 110, 122, 0.18);
                }
            """)
            header_shell_layout = QHBoxLayout(header_shell)
            header_shell_layout.setContentsMargins(8, 4, 8, 4)
            header_shell_layout.setSpacing(4)

            header_btn = QPushButton(title)
            header_btn.setCheckable(True)
            header_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            header_btn.setMinimumHeight(36)
            header_btn.setProperty("class", "accordion-header-btn")
            header_btn.setStyleSheet("""
                QPushButton[class="accordion-header-btn"] {
                    text-align: left;
                    font-weight: 700;
                    border: none;
                    border-radius: 0;
                    padding: 8px 6px;
                    background-color: transparent;
                }
            """)
            header_btn.clicked.connect(lambda _checked=False, key=section_key: self._on_right_section_header_clicked(key))
            header_shell_layout.addWidget(header_btn, 1)
            if header_actions is not None:
                header_shell_layout.addWidget(header_actions, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            container_layout.addWidget(header_shell)

            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(6)
            if top_widget is not None:
                content_layout.addWidget(top_widget)
            if list_widget is not None:
                list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                list_widget.setProperty("class", "embedded-list")
                list_widget.style().unpolish(list_widget)
                list_widget.style().polish(list_widget)
                content_layout.addWidget(list_widget)
            
            if button:
                content_layout.addWidget(button)

            container_layout.addWidget(content_widget, 1)
            self._right_sidebar_sections[section_key] = {
                "title": title,
                "header": header_btn,
                "header_shell": header_shell,
                "content": content_widget,
                "container": container,
            }
            return container

        # 1. Tasks Section
        self.tasks_sidebar_list = QListWidget()
        self.tasks_sidebar_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tasks_sidebar_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tasks_sidebar_list.customContextMenuRequested.connect(self.show_tasks_sidebar_context_menu)

        task_action_style = """
            QToolButton {
                border: none;
                border-radius: 8px;
                padding: 4px;
                background-color: transparent;
                color: #CFD8DC;
                font-size: 18px;
                font-weight: 700;
            }
            QToolButton:hover {
                background-color: rgba(84, 110, 122, 0.18);
            }
        """

        self.create_task_btn = QToolButton()
        self.create_task_btn.setText("+")
        self.create_task_btn.setToolTip("Create a new task")
        self.create_task_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_task_btn.setAutoRaise(True)
        self.create_task_btn.setFixedSize(28, 28)
        self.create_task_btn.setStyleSheet(task_action_style)
        self.create_task_btn.clicked.connect(lambda: self.open_tasks_tab(create_new=True))

        self.open_tasks_btn = QToolButton()
        self.open_tasks_btn.setText("⤢")
        self.open_tasks_btn.setToolTip("Open the full Tasks tab")
        self.open_tasks_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_tasks_btn.setAutoRaise(True)
        self.open_tasks_btn.setFixedSize(28, 28)
        self.open_tasks_btn.setStyleSheet(task_action_style)
        self.open_tasks_btn.clicked.connect(lambda: self.open_tasks_tab(create_new=False))

        self.tasks_header_actions = QWidget()
        tasks_header_layout = QHBoxLayout(self.tasks_header_actions)
        tasks_header_layout.setContentsMargins(0, 0, 0, 0)
        tasks_header_layout.setSpacing(2)
        tasks_header_layout.addWidget(self.create_task_btn)
        tasks_header_layout.addWidget(self.open_tasks_btn)

        tasks_section = create_section("tasks", "✅ Tasks", self.tasks_sidebar_list, header_actions=self.tasks_header_actions)
        right_layout.addWidget(tasks_section)
        self._right_sidebar_sections["tasks"]["index"] = right_layout.indexOf(tasks_section)

        # 2. Chat History Section
        self.sessions_list = QListWidget()
        self.sessions_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sessions_list.itemClicked.connect(self.on_chat_session_clicked)
        self.sessions_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sessions_list.customContextMenuRequested.connect(self.show_chat_sidebar_context_menu)

        self.new_chat_btn = QToolButton()
        self.new_chat_btn.setText("+")
        self.new_chat_btn.setToolTip("Start a new chat")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.setAutoRaise(True)
        self.new_chat_btn.setFixedSize(28, 28)
        self.new_chat_btn.setStyleSheet(task_action_style)
        self.new_chat_btn.clicked.connect(lambda: self.open_chat_tab(None))

        self.open_chat_history_btn = QToolButton()
        self.open_chat_history_btn.setText("⤢")
        self.open_chat_history_btn.setToolTip("Open the full Chat History tab")
        self.open_chat_history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_chat_history_btn.setAutoRaise(True)
        self.open_chat_history_btn.setFixedSize(28, 28)
        self.open_chat_history_btn.setStyleSheet(task_action_style)
        self.open_chat_history_btn.clicked.connect(self.open_chat_history_tab)

        self.chats_header_actions = QWidget()
        chats_header_layout = QHBoxLayout(self.chats_header_actions)
        chats_header_layout.setContentsMargins(0, 0, 0, 0)
        chats_header_layout.setSpacing(2)
        chats_header_layout.addWidget(self.new_chat_btn)
        chats_header_layout.addWidget(self.open_chat_history_btn)

        chat_section = create_section("chats", "💬 Chat History", self.sessions_list, header_actions=self.chats_header_actions)
        right_layout.addWidget(chat_section)
        self._right_sidebar_sections["chats"]["index"] = right_layout.indexOf(chat_section)
        
        # 3. Libretas (Notebooks) Section
        self.notebooks_list = QListWidget()
        self.notebooks_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.notebooks_list.itemClicked.connect(self.on_notebook_clicked)
        self.notebooks_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.notebooks_list.customContextMenuRequested.connect(self.show_notebooks_sidebar_context_menu)

        self.create_notebook_btn = QToolButton()
        self.create_notebook_btn.setText("+")
        self.create_notebook_btn.setToolTip("Create a new notebook")
        self.create_notebook_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_notebook_btn.setAutoRaise(True)
        self.create_notebook_btn.setFixedSize(28, 28)
        self.create_notebook_btn.setStyleSheet(task_action_style)
        self.create_notebook_btn.clicked.connect(self.create_notebook)

        self.open_notebooks_btn = QToolButton()
        self.open_notebooks_btn.setText("⤢")
        self.open_notebooks_btn.setToolTip("Open the full Notebooks tab")
        self.open_notebooks_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_notebooks_btn.setAutoRaise(True)
        self.open_notebooks_btn.setFixedSize(28, 28)
        self.open_notebooks_btn.setStyleSheet(task_action_style)
        self.open_notebooks_btn.clicked.connect(self.open_notebooks_list)

        self.notebooks_header_actions = QWidget()
        notebooks_header_layout = QHBoxLayout(self.notebooks_header_actions)
        notebooks_header_layout.setContentsMargins(0, 0, 0, 0)
        notebooks_header_layout.setSpacing(2)
        notebooks_header_layout.addWidget(self.create_notebook_btn)
        notebooks_header_layout.addWidget(self.open_notebooks_btn)

        nb_section = create_section("notebooks", "📓 Notebooks", self.notebooks_list, header_actions=self.notebooks_header_actions)
        right_layout.addWidget(nb_section)
        self._right_sidebar_sections["notebooks"]["index"] = right_layout.indexOf(nb_section)

        # 4. Tags Section
        self.collections_list = QListWidget()
        self.collections_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.collections_list.itemClicked.connect(self.on_collection_clicked)
        self.collections_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.collections_list.customContextMenuRequested.connect(self.show_tags_sidebar_context_menu)

        self.new_tag_chat_btn = QToolButton()
        self.new_tag_chat_btn.setText("+")
        self.new_tag_chat_btn.setToolTip("Start a chat for the selected tag")
        self.new_tag_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_tag_chat_btn.setAutoRaise(True)
        self.new_tag_chat_btn.setFixedSize(28, 28)
        self.new_tag_chat_btn.setStyleSheet(task_action_style)
        self.new_tag_chat_btn.clicked.connect(self.open_selected_tag_chat)

        self.open_collections_btn = QToolButton()
        self.open_collections_btn.setText("⤢")
        self.open_collections_btn.setToolTip("Open the full Collections tab")
        self.open_collections_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_collections_btn.setAutoRaise(True)
        self.open_collections_btn.setFixedSize(28, 28)
        self.open_collections_btn.setStyleSheet(task_action_style)
        self.open_collections_btn.clicked.connect(self.open_collections_list)

        self.tags_header_actions = QWidget()
        tags_header_layout = QHBoxLayout(self.tags_header_actions)
        tags_header_layout.setContentsMargins(0, 0, 0, 0)
        tags_header_layout.setSpacing(2)
        tags_header_layout.addWidget(self.new_tag_chat_btn)
        tags_header_layout.addWidget(self.open_collections_btn)

        tags_section = create_section("tags", "🏷️ Tags", self.collections_list, header_actions=self.tags_header_actions)
        right_layout.addWidget(tags_section)
        self._right_sidebar_sections["tags"]["index"] = right_layout.indexOf(tags_section)

        # 5. Active Chat Context Section
        self.chat_context_panel = ContextManagerPanel(
            self.db,
            self.notebook_db,
            parent=right_panel,
            show_header=False,
            interactive=False,
        )
        self.chat_context_section = create_section(
            "chat_context",
            "💬 Active Chat Context",
            top_widget=self.chat_context_panel,
        )
        self._right_sidebar_sections["chat_context"]["context_panel"] = self.chat_context_panel
        right_layout.addWidget(self.chat_context_section)
        self._right_sidebar_sections["chat_context"]["index"] = right_layout.indexOf(self.chat_context_section)
        self._right_sidebar_sections["chat_context"]["container"].setVisible(False)

        right_layout.addStretch(1)
        self._right_sidebar_bottom_spacer_index = right_layout.count() - 1

        # Independent bottom section: Settings (outside accordion logic)
        right_settings_section = QWidget()
        right_settings_layout = QVBoxLayout(right_settings_section)
        right_settings_layout.setContentsMargins(0, 6, 0, 0)
        right_settings_layout.setSpacing(6)

        self.right_settings_label = QLabel("⚙️ Settings")
        self.right_settings_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #2196F3;")
        right_settings_layout.addWidget(self.right_settings_label)

        self.right_settings_btn = QPushButton("Open Settings")
        self.right_settings_btn.setProperty("class", "calendar-nav-btn")
        self.right_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.right_settings_btn.setMinimumHeight(34)
        self.right_settings_btn.clicked.connect(self.open_settings_tab)
        right_settings_layout.addWidget(self.right_settings_btn)

        right_layout.addWidget(right_settings_section)
        self._set_active_right_section("tasks")
        
        self.splitter.addWidget(right_panel)

        self.floating_chat_bar = QFrame(central_widget)
        self.floating_chat_bar.setObjectName("floatingChatBar")
        self.floating_chat_bar.setStyleSheet("""
            QFrame#floatingChatBar {
                background-color: transparent;
                border: none;
            }
        """)
        self.floating_chat_bar.setVisible(False)
        self.floating_chat_layout = QHBoxLayout(self.floating_chat_bar)
        self.floating_chat_layout.setContentsMargins(0, 0, 0, 0)
        self.floating_chat_layout.setSpacing(12)
        self.floating_chat_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        self.floating_chat_bar.raise_()

        # Set initial sizes for the three panels
        # Left: 300 (min), Middle: 700 (rest), Right: 300 (min)
        self.splitter.setSizes([300, 700, 300])
        
        # Enforce stretch factors to ensure right panel takes up space
        self.splitter.setStretchFactor(0, 0) # Left panel doesn't stretch
        self.splitter.setStretchFactor(1, 1) # Middle panel stretches
        self.splitter.setStretchFactor(2, 0) # Right panel doesn't stretch
        
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, False)
        
        # Initialize RAG Engine from settings
        settings = QSettings("Hectronic", "Secretario")
        self._build_rag_engine(
            {
                "enabled": settings.value("rag_enabled", True, type=bool),
                "persist_directory": settings.value("rag_persist_directory", "chroma_db"),
                "safe_delete_mode": settings.value("rag_safe_delete_mode", True, type=bool),
                "subprocess_upsert_mode": settings.value("rag_subprocess_upsert_mode", True, type=bool),
                "subprocess_query_mode": settings.value("rag_subprocess_query_mode", True, type=bool),
            },
            reason="startup",
        )

    def _on_right_section_header_clicked(self, section_key):
        if self._active_right_section == section_key:
            self._set_active_right_section(None)
        else:
            self._set_active_right_section(section_key)

    def _set_active_right_section(self, section_key):
        if section_key is not None and section_key not in self._right_sidebar_sections:
            return

        self._active_right_section = section_key
        if section_key not in (None, "chat_context"):
            self._right_sidebar_last_non_chat_section = section_key
        for key, section in self._right_sidebar_sections.items():
            is_active = section_key is not None and key == section_key
            section["header"].blockSignals(True)
            section["header"].setChecked(is_active)
            prefix = "▾ " if is_active else "▸ "
            section["header"].setText(f"{prefix}{section['title']}")
            section["header"].blockSignals(False)
            header_shell = section.get("header_shell")
            if header_shell is not None:
                header_shell.setProperty("active", "true" if is_active else "false")
                header_shell.style().unpolish(header_shell)
                header_shell.style().polish(header_shell)
            section["content"].setVisible(is_active)
            idx = section.get("index")
            if self._right_sidebar_layout is not None and idx is not None:
                self._right_sidebar_layout.setStretch(idx, 1 if (section_key is not None and is_active) else 0)
        if self._right_sidebar_layout is not None and self._right_sidebar_bottom_spacer_index is not None:
            self._right_sidebar_layout.setStretch(
                self._right_sidebar_bottom_spacer_index,
                0 if section_key is not None else 1,
            )

    def _on_central_tab_changed(self, _index):
        self.refresh_tasks_sidebar()
        self._sync_chat_context_section()

    def _current_chat_widget(self):
        widget = self.central_tabs.currentWidget() if hasattr(self, "central_tabs") else None
        return widget if isinstance(widget, ChatWidget) else None

    def _sync_chat_context_section(self, chat_widget=None):
        section = self._right_sidebar_sections.get("chat_context")
        if section is None:
            return

        if chat_widget is None:
            chat_widget = self._current_chat_widget()

        container = section.get("container")
        if not isinstance(chat_widget, ChatWidget):
            if container is not None:
                container.setVisible(False)
            if self._active_right_section == "chat_context":
                fallback = self._right_sidebar_last_non_chat_section
                if fallback not in self._right_sidebar_sections:
                    fallback = "tasks" if "tasks" in self._right_sidebar_sections else None
                self._set_active_right_section(fallback)
            return

        if container is not None:
            container.setVisible(True)
        sidebar_panel = section.get("context_panel")
        if sidebar_panel is not None and hasattr(chat_widget, "context_panel"):
            try:
                sidebar_panel.restore_from_panel(chat_widget.context_panel)
            except Exception:
                logging.exception("Failed to sync active chat context sidebar")
        self._set_active_right_section("chat_context")

    def show_welcome_screen(self):
        self.welcome_widget = WelcomeWidget(self.db)
        self.welcome_widget.new_recording_requested.connect(self.start_new_recording)
        self.welcome_widget.new_note_requested.connect(lambda: self.open_note_tab(None))
        self.welcome_widget.search_triggered.connect(self.perform_welcome_search)
        self.welcome_widget.result_clicked.connect(self.open_item_tab)
        self.welcome_widget.new_chat_requested.connect(lambda: self.open_chat_tab(None))
        self.welcome_widget.ask_chat_with_context_requested.connect(self.open_chat_tab_from_current_context)
        self.welcome_widget.import_audio_requested.connect(self.import_audio_file)
        self.welcome_widget.notebooks_requested.connect(self.open_notebooks_list)
        self.welcome_widget.tools_requested.connect(lambda: self.open_tools_tab())
        self.welcome_widget.settings_requested.connect(self.open_settings_tab)
        self.welcome_widget.generate_daily_summary_requested.connect(self.generate_today_daily_summary)
        self.welcome_widget.status_message_requested.connect(self.handle_status_message)
        
        # Add as first tab, not closable
        self.central_tabs.addTab(self.welcome_widget, "Welcome")
        self._set_tab_action_buttons(self.welcome_widget)

    def open_item_tab(self, record_id):
        """Open a tab for a record, deciding between recording and note."""
        record = self.db.fetch_record(record_id)
        if not record:
            return
            
        type_ = record.get('type', 'recording')
        if type_ == 'note':
            self.open_note_tab(record_id)
        else:
            self.open_recording_tab(record_id)

    def generate_today_daily_summary(self):
        """Queue generation/update of today's daily summary."""
        from datetime import date
        today_str = date.today().isoformat()
        self.summary_task_queue.enqueue_daily_summary({
            "date": today_str,
            "tags_filter": "",
            "source": "startup",
        })

    def start_new_recording(self, config):
        """Start a new recording with the given configuration."""
        logging.info(f"Starting new recording with config: {config}")
        self._log_user_settings_snapshot("start_new_recording")
        # Check if we have a recording in progress already
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, RecordingInProgressWidget):
                self.central_tabs.setCurrentIndex(i)
                return
        
        # Set device on recorder
        if config.get("device_index") is not None:
            self.recorder.set_device(config["device_index"])
            
        # Set system audio capture flag
        self.recorder.set_capture_machine_audio(config.get("capture_system_audio", False))
        
        # New Recording Flow with config
        rec_widget = RecordingInProgressWidget(recorder=self.recorder, config=config)
        rec_widget.finished.connect(lambda path, cfg, w=rec_widget: self.on_recording_finished(path, cfg, w))
        rec_widget.cancelled.connect(lambda w=rec_widget: self.close_tab(self.central_tabs.indexOf(w)))
        
        index = self.central_tabs.addTab(rec_widget, "Recording...")
        self.central_tabs.setCurrentIndex(index)

    def _recording_tab_title(self, record):
        if not record:
            return "Recording"
        return record['title'] if record.get('title') else f"Recording {record['id']}"

    def _find_recording_tabs(self, record_id):
        tabs = []
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                tabs.append(widget)
        return tabs

    def _sync_recording_tab_titles(self, record_id):
        record = self.db.fetch_record(record_id)
        title = self._recording_tab_title(record) if record else f"Recording {record_id}"
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                self.central_tabs.setTabText(i, title)

    def _handle_recording_widget_saved(self, rec_widget):
        record_id = getattr(rec_widget, "current_record_id", None)
        if record_id is None:
            return
        self.load_history()
        self.request_sidebar_reload(include_tags=True, include_history=True)
        self._sync_recording_tab_titles(record_id)

    def _handle_recording_widget_deleted(self, record_id):
        self._close_recording_tabs(record_id)
        self.load_history()
        self.request_sidebar_reload(include_tags=True, include_history=True)

    def _close_recording_tabs(self, record_id):
        removed = False
        for i in range(self.central_tabs.count() - 1, -1, -1):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                if hasattr(widget, "cleanup"):
                    try:
                        widget.cleanup()
                    except Exception:
                        pass
                self.central_tabs.removeTab(i)
                widget.deleteLater()
                removed = True
        if removed and self.central_tabs.count() == 0:
            self.show_welcome_screen()
        if removed:
            self._sync_chat_context_section()

    def open_recording_tab(self, record_id, config=None, force_new=False):
        """Open a recording tab for an existing record."""
        # Check if already open
        if record_id is not None and not force_new:
            for i in range(self.central_tabs.count()):
                widget = self.central_tabs.widget(i)
                if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                    self.central_tabs.setCurrentIndex(i)
                    return widget

        # Create new tab for existing recording
        rec_widget = RecordingWidget(self.rag, recorder=self.recorder, record_id=record_id, task_queue=self.summary_task_queue)
        rec_widget.recording_saved.connect(lambda w=rec_widget: self._handle_recording_widget_saved(w))
        rec_widget.recording_deleted.connect(self._handle_recording_widget_deleted)
        rec_widget.status_changed.connect(self.handle_status_message)
        rec_widget.progress_changed.connect(self.handle_progress)
        rec_widget.start_chat_requested.connect(lambda contexts: self.open_chat_tab(initial_contexts=contexts))
        rec_widget.open_audio_editor_requested.connect(self.open_recording_editor_tab)
        rec_widget.close_requested.connect(lambda: self.close_tab(self.central_tabs.indexOf(rec_widget)))
        
        # If config is provided, set the widget's transcription settings
        if config:
            rec_widget.set_transcription_config(config)
        
        title = "New Recording"
        if record_id:
            record = self.db.fetch_record(record_id)
            if not isinstance(record, dict):
                records = self.db.fetch_all()
                record = next((r for r in records if r['id'] == record_id), None)
            if record:
                title = self._recording_tab_title(record)

        index = self.central_tabs.addTab(rec_widget, title)
        self.central_tabs.setCurrentIndex(index)
        return rec_widget

    def open_recording_editor_tab(self, record_id, config=None):
        """Open a dedicated audio-editing tab for an existing recording."""
        rec_widget = AudioEditorWidget(
            self.rag,
            recorder=self.recorder,
            record_id=record_id,
            task_queue=self.summary_task_queue,
        )
        rec_widget.recording_saved.connect(lambda w=rec_widget: self._handle_recording_widget_saved(w))
        rec_widget.recording_deleted.connect(self._handle_recording_widget_deleted)
        rec_widget.status_changed.connect(self.handle_status_message)
        rec_widget.progress_changed.connect(self.handle_progress)
        rec_widget.close_requested.connect(lambda: self.close_tab(self.central_tabs.indexOf(rec_widget)))

        title = "Audio Editor"
        if record_id:
            record = self.db.fetch_record(record_id)
            if not isinstance(record, dict):
                records = self.db.fetch_all()
                record = next((r for r in records if r['id'] == record_id), None)
            if record:
                title = f"{self._recording_tab_title(record)} - Editor"

        index = self.central_tabs.addTab(rec_widget, title)
        self.central_tabs.setCurrentIndex(index)
        return rec_widget

    def open_note_tab(self, record_id=None):
        """Open a note tab for a new or existing note."""
        # Check if already open
        if record_id:
            for i in range(self.central_tabs.count()):
                widget = self.central_tabs.widget(i)
                if isinstance(widget, NoteWidget) and widget.current_record_id == record_id:
                    self.central_tabs.setCurrentIndex(i)
                    return widget

        note_widget = NoteWidget(self.rag, record_id=record_id, task_queue=self.summary_task_queue)
        note_widget.note_saved.connect(self.load_history)
        note_widget.status_changed.connect(self.handle_status_message)
        note_widget.progress_changed.connect(self.handle_progress)
        note_widget.close_requested.connect(lambda: self.close_tab(self.central_tabs.indexOf(note_widget)))
        
        title = "New Note"
        if record_id:
            record = self.db.fetch_record(record_id)
            if record:
                title = record['title'] if record['title'] else f"Note {record['id']}"
        
        index = self.central_tabs.addTab(note_widget, title)
        self.central_tabs.setCurrentIndex(index)
        return note_widget

    def on_recording_finished(self, file_path, config, widget):
        """Handle recording finished - save to DB and start transcription with config."""
        self._log_user_settings_snapshot("on_recording_finished")
        logging.info(
            "on_recording_finished called with file_path=%s widget=%s config_keys=%s",
            file_path,
            type(widget).__name__ if widget else None,
            sorted(list((config or {}).keys())),
        )
        # Close the recording widget
        index = self.central_tabs.indexOf(widget)
        if index != -1:
            self.central_tabs.removeTab(index)
            widget.deleteLater()
            logging.info("RecordingInProgress tab closed at index=%s", index)
        else:
            logging.warning("RecordingInProgress widget tab not found during finish flow.")
        
        try:
            filename = os.path.basename(file_path)
            # Use title from config, fallback to filename
            title = config.get("title") or filename
            recording_notes = config.get("recording_notes", "")
            pending_tasks = config.get("pending_tasks") or []
            logging.info(
                "Persisting new recording filename=%s title=%s notes_len=%d pending_tasks=%d",
                filename,
                title,
                len(recording_notes),
                len(pending_tasks),
            )
            # Create DB entry to get an ID
            record_id = self.db.save(filename, "", 0.0, title=title, recording_notes=recording_notes)
            logging.info("DB save completed with record_id=%s", record_id)
            
            # Update tags if provided
            tags = config.get("tags", "")
            if tags:
                self.db.update_tags(record_id, tags)
                logging.info("Tags saved for record_id=%s tags=%s", record_id, tags)

            # Persist quick tasks captured during recording.
            for task_content in pending_tasks:
                clean_task = str(task_content or "").strip()
                if clean_task:
                    try:
                        self.db.save_task(record_id=record_id, content=clean_task, tags=tags or None)
                        logging.info("Saved quick task for record_id=%s: %s", record_id, clean_task)
                    except Exception:
                        logging.exception("Failed saving quick task for record_id=%s", record_id)
            
            # Refresh sidebar to show new recording with title
            self.request_sidebar_reload(include_tags=True, include_history=True)
            logging.info("Requested sidebar reload after recording finish for record_id=%s", record_id)
            
            # Open standard recording tab with config
            rec_widget = self.open_recording_tab(record_id, config)
            logging.info("Opened recording tab for record_id=%s widget_created=%s", record_id, bool(rec_widget))
            
            # Trigger transcription with config
            if rec_widget and isinstance(rec_widget, RecordingWidget):
                logging.info("Starting transcription with config for record_id=%s file=%s", record_id, file_path)
                rec_widget.start_transcription_with_config(file_path, config)
                
        except Exception as e:
            logging.exception("Failed while handling recording completion flow.")
            QMessageBox.critical(self, "Error", f"Failed to save recording: {e}")



    def _connect_chat_widget(self, chat_widget):
        chat_widget.session_updated.connect(self.load_chat_sessions)
        chat_widget.float_requested.connect(self.float_chat_widget)
        chat_widget.tab_requested.connect(self.dock_chat_widget_to_tab)
        chat_widget.minimize_requested.connect(self.minimize_floating_chat)
        chat_widget.restore_requested.connect(self.restore_floating_chat)
        chat_widget.close_requested.connect(self.close_chat_widget)
        chat_widget.title_changed.connect(self._sync_chat_widget_title)
        chat_widget.context_panel.context_changed.connect(
            lambda w=chat_widget: self._sync_chat_context_section(w)
        )

    def _find_chat_tab_index(self, session_id):
        if session_id is None:
            return -1
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, ChatWidget) and widget.current_session_id == session_id:
                return i
        return -1

    def _find_floating_chat_host(self, session_id):
        if session_id is None:
            return None
        for host in self.floating_chat_hosts:
            widget = host.property("chat_widget")
            if isinstance(widget, ChatWidget) and widget.current_session_id == session_id:
                return host
        return None

    def _is_dark_theme(self):
        from PyQt6.QtGui import QPalette
        app = QApplication.instance()
        sheet = (app.styleSheet() if app else "").lower()
        if "#2b2b2b" in sheet and "#eeeeee" in sheet:
            return True
        if "#f5f5f5" in sheet and "#333333" in sheet:
            return False
        return self.palette().color(QPalette.ColorRole.Window).lightness() < 128

    def _apply_floating_chat_host_style(self, host):
        if host is None:
            return
        is_dark = self._is_dark_theme()
        border_color = "rgba(100, 181, 246, 0.55)" if is_dark else "rgba(84, 110, 122, 0.45)"
        bg_color = "#232831" if is_dark else "#f5f7fb"
        handle_color = "#d7e7ff" if is_dark else "#1f5f99"
        handle_bg = "rgba(20, 26, 34, 0.82)" if is_dark else "rgba(255, 255, 255, 0.92)"
        host.setStyleSheet(f"""
            QFrame#floatingChatHost {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        host.resize_handle.setText("◤")
        host.resize_handle.setStyleSheet(
            "QLabel#floatingChatResizeHandle {"
            f"color: {handle_color};"
            f"background-color: {handle_bg};"
            "border: 1px solid rgba(120, 140, 160, 0.35);"
            "border-radius: 7px;"
            "font-size: 16px;"
            "font-weight: 700;"
            "padding: 0px;"
            "}"
        )

    def _wrap_floating_chat(self, chat_widget):
        host = FloatingChatHost()
        host.setObjectName("floatingChatHost")
        host.setProperty("chat_widget", chat_widget)
        host.setProperty("chat_minimized", False)
        host.setProperty(
            "normal_size",
            QSize(FloatingChatHost.DEFAULT_WIDTH, FloatingChatHost.DEFAULT_HEIGHT),
        )
        self._apply_floating_chat_host_style(host)
        host.set_size_bounds(
            QSize(FloatingChatHost.MIN_WIDTH, FloatingChatHost.MIN_HEIGHT),
            QSize(FloatingChatHost.MAX_WIDTH, FloatingChatHost.MAX_HEIGHT),
        )
        host.size_changed.connect(lambda h=host: self._on_floating_chat_host_size_changed(h))
        host.set_preferred_size(QSize(FloatingChatHost.DEFAULT_WIDTH, FloatingChatHost.DEFAULT_HEIGHT))
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(chat_widget)
        self._set_floating_chat_minimized(host, False)
        return host

    def _on_floating_chat_host_size_changed(self, host):
        if host is None or host.property("chat_minimized"):
            self._refresh_floating_chat_bar()
            return
        host.setProperty("normal_size", QSize(host.size()))
        self._refresh_floating_chat_bar()

    def _set_floating_chat_minimized(self, host, minimized):
        if host is None:
            return
        chat_widget = host.property("chat_widget")
        if chat_widget is None:
            return
        minimized = bool(minimized)
        host.setProperty("chat_minimized", minimized)
        chat_widget.setVisible(True)
        chat_widget.set_floating_minimized(minimized)
        if minimized:
            if not host.property("normal_size"):
                host.setProperty("normal_size", QSize(host.size()))
            else:
                host.setProperty("normal_size", QSize(host.size()))
            host.set_size_bounds(
                QSize(FloatingChatHost.MINIMIZED_WIDTH, FloatingChatHost.MINIMIZED_HEIGHT),
                QSize(FloatingChatHost.MINIMIZED_WIDTH, FloatingChatHost.MINIMIZED_HEIGHT),
            )
            host.set_resize_enabled(False)
            host.set_preferred_size(
                QSize(FloatingChatHost.MINIMIZED_WIDTH, FloatingChatHost.MINIMIZED_HEIGHT)
            )
            return

        normal_size = host.property("normal_size")
        if not isinstance(normal_size, QSize):
            normal_size = QSize(FloatingChatHost.DEFAULT_WIDTH, FloatingChatHost.DEFAULT_HEIGHT)
        host.set_size_bounds(
            QSize(FloatingChatHost.MIN_WIDTH, FloatingChatHost.MIN_HEIGHT),
            QSize(FloatingChatHost.MAX_WIDTH, FloatingChatHost.MAX_HEIGHT),
        )
        host.set_resize_enabled(True)
        host.set_preferred_size(normal_size)

    def _find_floating_chat_host_by_widget(self, chat_widget):
        return next((h for h in self.floating_chat_hosts if h.property("chat_widget") is chat_widget), None)

    def _remove_floating_host(self, host):
        if host is None:
            return
        self.floating_chat_layout.removeWidget(host)
        if host in self.floating_chat_hosts:
            self.floating_chat_hosts.remove(host)
        host.deleteLater()
        self._refresh_floating_chat_bar()

    def _refresh_floating_chat_bar(self):
        visible = bool(self.floating_chat_hosts)
        self.floating_chat_bar.setVisible(visible)
        if visible:
            for host in self.floating_chat_hosts:
                self._apply_floating_chat_host_style(host)
                self.floating_chat_layout.setAlignment(host, Qt.AlignmentFlag.AlignBottom)
            # Use singleShot to let the layout settle before calculating positions
            QTimer.singleShot(0, self._reposition_floating_chat_bar)
            self.floating_chat_bar.raise_()

    def _reposition_floating_chat_bar(self):
        if not hasattr(self, "floating_chat_bar") or self.floating_chat_bar is None:
            return
        parent = self.centralWidget()
        if parent is None:
            return
        
        margin = 16
        spacing = self.floating_chat_layout.spacing()
        
        # Calculate required width based on children
        total_width = 0
        max_height = 0
        visible_hosts = 0
        for i in range(self.floating_chat_layout.count()):
            item = self.floating_chat_layout.itemAt(i)
            widget = item.widget()
            if widget and widget.isVisible():
                total_width += widget.width()
                max_height = max(max_height, widget.height())
                visible_hosts += 1
        
        if visible_hosts > 0:
            total_width += spacing * (visible_hosts - 1)
        
        available_width = max(260, parent.width() - (margin * 2))
        width = min(total_width, available_width)
        height = max_height
        
        # Add layout margins to the final size
        width += self.floating_chat_layout.contentsMargins().left() + self.floating_chat_layout.contentsMargins().right()
        height += self.floating_chat_layout.contentsMargins().top() + self.floating_chat_layout.contentsMargins().bottom()

        self.floating_chat_bar.resize(width, height)
        
        status = self.statusBar()
        if status is not None and status.isVisible():
            status_top = parent.mapFrom(self, QPoint(0, status.geometry().top())).y()
            y = status_top - height
        else:
            y = parent.height() - height
            
        x = parent.width() - width - margin
        self.floating_chat_bar.move(x, max(0, y))

    def changeEvent(self, event):
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.StyleChange,
        ) and hasattr(self, "floating_chat_bar"):
            self._refresh_floating_chat_bar()
        super().changeEvent(event)

    def _tab_title_for_chat(self, chat_widget):
        return chat_widget.get_chat_title()

    def _set_tab_action_buttons(self, widget):
        if widget is None:
            return
        index = self.central_tabs.indexOf(widget)
        if index == -1:
            return

        tab_bar = self.central_tabs.tabBar()

        if isinstance(widget, WelcomeWidget):
            tab_bar.setTabButton(index, QTabBar.ButtonPosition.LeftSide, None)
            tab_bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, None)
            return

        if not isinstance(widget, ChatWidget):
            return

        buttons = QWidget(tab_bar)
        layout = QHBoxLayout(buttons)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        float_btn = QToolButton(buttons)
        float_btn.setText("↗")
        float_btn.setToolTip("Move chat to floating window")
        float_btn.setAutoRaise(True)
        float_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        float_btn.setFixedSize(18, 18)
        float_btn.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 6px;
                padding: 0px;
                background: transparent;
                color: #6f8698;
                font-size: 11px;
                font-weight: 700;
            }
            QToolButton:hover {
                background-color: rgba(33, 150, 243, 0.16);
                color: #2196F3;
            }
        """)
        float_btn.clicked.connect(lambda _checked=False, w=widget: self.float_chat_widget(w))
        layout.addWidget(float_btn)

        close_btn = QToolButton(buttons)
        close_btn.setText("×")
        close_btn.setToolTip("Close tab")
        close_btn.setAutoRaise(True)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 6px;
                padding: 0px;
                background: transparent;
                color: #6f8698;
                font-size: 12px;
                font-weight: 700;
            }
            QToolButton:hover {
                background-color: rgba(244, 67, 54, 0.15);
                color: #f44336;
            }
        """)
        close_btn.clicked.connect(
            lambda _checked=False, w=widget: self.close_tab(self.central_tabs.indexOf(w))
        )
        layout.addWidget(close_btn)

        tab_bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, buttons)

    def _sync_chat_widget_title(self, chat_widget, title):
        tab_index = self.central_tabs.indexOf(chat_widget)
        if tab_index != -1:
            self.central_tabs.setTabText(tab_index, title)
        host = self._find_floating_chat_host_by_widget(chat_widget)
        if host is not None:
            host.setToolTip(title)

    def float_chat_widget(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        host = self._find_floating_chat_host_by_widget(chat_widget)
        if host is not None:
            self._set_floating_chat_minimized(host, False)
            return
        tab_index = self.central_tabs.indexOf(chat_widget)
        if tab_index != -1:
            self.central_tabs.removeTab(tab_index)
        chat_widget.setParent(None)
        chat_widget.set_display_mode("floating")
        host = self._wrap_floating_chat(chat_widget)
        self.floating_chat_hosts.append(host)
        self.floating_chat_layout.insertWidget(
            self.floating_chat_layout.count(),
            host,
            0,
            Qt.AlignmentFlag.AlignBottom,
        )
        self._sync_chat_widget_title(chat_widget, chat_widget.get_chat_title())
        self._refresh_floating_chat_bar()
        self._sync_chat_context_section()

    def minimize_floating_chat(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        host = self._find_floating_chat_host_by_widget(chat_widget)
        if host is None:
            self.float_chat_widget(chat_widget)
            host = self._find_floating_chat_host_by_widget(chat_widget)
        self._set_floating_chat_minimized(host, True)
        self._refresh_floating_chat_bar()

    def restore_floating_chat(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        host = self._find_floating_chat_host_by_widget(chat_widget)
        self._set_floating_chat_minimized(host, False)
        self._refresh_floating_chat_bar()

    def dock_chat_widget_to_tab(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        host = self._find_floating_chat_host_by_widget(chat_widget)
        if host is None:
            tab_index = self.central_tabs.indexOf(chat_widget)
            if tab_index != -1:
                self.central_tabs.setCurrentIndex(tab_index)
            return
        self.floating_chat_layout.removeWidget(host)
        if host in self.floating_chat_hosts:
            self.floating_chat_hosts.remove(host)
        chat_widget.setParent(None)
        chat_widget.set_display_mode("tab")
        host.deleteLater()
        title = self._tab_title_for_chat(chat_widget)
        index = self.central_tabs.addTab(chat_widget, title)
        self.central_tabs.setCurrentIndex(index)
        self._set_tab_action_buttons(chat_widget)
        self._refresh_floating_chat_bar()
        self._sync_chat_context_section(chat_widget)

    def close_chat_widget(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        tab_index = self.central_tabs.indexOf(chat_widget)
        if tab_index != -1:
            self.close_tab(tab_index)
            return
        self.close_floating_chat(chat_widget)
        self._sync_chat_context_section()

    def open_chat_tab(self, session_id=None, initial_contexts=None):
        if not self.rag:
            QMessageBox.warning(self, "RAG Error", "RAG Engine not initialized.")
            return
        
        # Check if already open (only for sessions)
        if session_id:
            tab_index = self._find_chat_tab_index(session_id)
            if tab_index != -1:
                self.central_tabs.setCurrentIndex(tab_index)
                self._sync_chat_context_section(self.central_tabs.widget(tab_index))
                return self.central_tabs.widget(tab_index)
            floating_host = self._find_floating_chat_host(session_id)
            if floating_host is not None:
                chat_widget = floating_host.property("chat_widget")
                self.dock_chat_widget_to_tab(chat_widget)
                return chat_widget

        chat_widget = ChatWidget(self.rag, session_id, self, initial_contexts=initial_contexts)
        self._connect_chat_widget(chat_widget)
        
        title = self._tab_title_for_chat(chat_widget)
        
        index = self.central_tabs.addTab(chat_widget, title)
        self.central_tabs.setCurrentIndex(index)
        self._set_tab_action_buttons(chat_widget)
        self._sync_chat_context_section(chat_widget)
        return chat_widget

    def open_floating_chat(self, session_id=None, initial_contexts=None):
        chat_widget = self.open_chat_tab(session_id=session_id, initial_contexts=initial_contexts)
        if isinstance(chat_widget, ChatWidget):
            self.float_chat_widget(chat_widget)
        return chat_widget

    def open_chat_tab_from_current_context(self):
        tag = self.tag_filter_combo.currentText() if hasattr(self, "tag_filter_combo") else "All"
        tags_str = "" if not tag or tag == "All" else tag
        chat_widget = self.open_chat_tab(None)
        if isinstance(chat_widget, ChatWidget):
            chat_widget.update_from_global_selection(self.current_week_monday, self.current_date_filter, tags_str)

    def open_chat_history_tab(self):
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, ChatHistoryWidget):
                self.central_tabs.setCurrentIndex(i)
                return widget

        history_widget = ChatHistoryWidget(self)
        history_widget.session_requested.connect(self.open_chat_tab)
        history_widget.session_delete_requested.connect(self.delete_chat_session_by_id)
        history_widget.set_sessions(self.db.fetch_chat_sessions())
        index = self.central_tabs.addTab(history_widget, "💬 Chat History")
        self.central_tabs.setCurrentIndex(index)
        return history_widget

    def open_tools_tab(self, tab_index=0):
        """Open the unified Tools tab, optionally switching to a specific sub-tab."""
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, ToolsWidget):
                self.central_tabs.setCurrentIndex(i)
                widget.show_tab(tab_index)
                return

        tools_widget = ToolsWidget(self.db, self.notebook_db, task_queue=self.summary_task_queue)
        
        index = self.central_tabs.addTab(tools_widget, "⚙️ Tools")
        self.central_tabs.setCurrentIndex(index)
        tools_widget.show_tab(tab_index)

    def open_tasks_tab(self, create_new=False):
        """Open a dedicated tab with incomplete tasks."""
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, TasksListWidget):
                self.central_tabs.setCurrentIndex(i)
                tag = self.tag_filter_combo.currentText()
                tags_filter = tag if tag != "All" else None
                widget.set_global_filters(self.current_week_monday, self.current_date_filter, tags_filter)
                widget.refresh()
                if create_new:
                    widget.open_create_dialog()
                return

        tasks_widget = TasksListWidget(self.db, limit=None)
        tasks_widget.open_recording_requested.connect(self.open_recording_tab)
        tasks_widget.tasks_changed.connect(self.refresh_tasks_sidebar)
        tag = self.tag_filter_combo.currentText()
        tags_filter = tag if tag != "All" else None
        tasks_widget.set_global_filters(self.current_week_monday, self.current_date_filter, tags_filter)
        index = self.central_tabs.addTab(tasks_widget, "✅ Tasks")
        self.central_tabs.setCurrentIndex(index)
        if create_new:
            tasks_widget.open_create_dialog()

    def close_tab(self, index):
        widget = self.central_tabs.widget(index)
        if widget is None:
            return
        if isinstance(widget, WelcomeWidget):
             # Maybe don't allow closing welcome widget?
             return 
        if isinstance(widget, RecordingInProgressWidget):
            if getattr(widget, "recording_started", False):
                widget.finish_recording()
                return
        if isinstance(widget, RecordingWidget):
            if hasattr(widget, "has_unsaved_changes") and widget.has_unsaved_changes():
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    "This recording has unsaved changes. Save them before closing?",
                    QMessageBox.StandardButton.Save
                    | QMessageBox.StandardButton.Discard
                    | QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                if reply == QMessageBox.StandardButton.Save:
                    if hasattr(widget, "save_all_changes") and not widget.save_all_changes():
                        return
        if hasattr(widget, "cleanup"):
            try:
                widget.cleanup()
            except Exception:
                pass
             
        self.central_tabs.removeTab(index)
        widget.deleteLater()
        
        if self.central_tabs.count() == 0:
            self.show_welcome_screen()
        self._sync_chat_context_section()

    def close_floating_chat(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        host = self._find_floating_chat_host_by_widget(chat_widget)
        if host is None:
            return
        if hasattr(chat_widget, "cleanup"):
            try:
                chat_widget.cleanup()
            except Exception:
                pass
        chat_widget.setParent(None)
        self._remove_floating_host(host)
        chat_widget.deleteLater()

    def show_tab_context_menu(self, point):
        index = self.central_tabs.tabBar().tabAt(point)
        if index == -1:
            return

        menu = QMenu(self)
        widget = self.central_tabs.widget(index)

        if isinstance(widget, ChatWidget):
            float_action = QAction("Move to Floating Window", self)
            float_action.triggered.connect(lambda: self.float_chat_widget(widget))
            menu.addAction(float_action)
            menu.addSeparator()
        elif isinstance(widget, RecordingWidget):
            editor_action = QAction("Open Audio Editor Tab", self)
            editor_action.triggered.connect(
                lambda: self.open_recording_editor_tab(widget.current_record_id)
            )
            menu.addAction(editor_action)
            menu.addSeparator()
        
        close_action = QAction("Close", self)
        close_action.triggered.connect(lambda: self.close_tab(index))
        menu.addAction(close_action)
        
        close_others_action = QAction("Close Others", self)
        close_others_action.triggered.connect(lambda: self.close_other_tabs(index))
        menu.addAction(close_others_action)
        
        close_all_action = QAction("Close All", self)
        close_all_action.triggered.connect(self.close_all_tabs)
        menu.addAction(close_all_action)
        
        menu.exec(self.central_tabs.mapToGlobal(point))

    def show_history_item_context_menu(self, point):
        item = self.history_list.itemAt(point)
        if item is None:
            return

        data = item.data(Qt.ItemDataRole.UserRole) or {}
        item_type = data.get("type", "recording")
        menu = QMenu(self)

        if item_type == "recording":
            open_action = QAction("Open", self)
            open_action.triggered.connect(lambda: self.open_recording_tab(data["id"]))
            open_new_action = QAction("Open Audio Editor Tab", self)
            open_new_action.triggered.connect(
                lambda: self.open_recording_editor_tab(data["id"])
            )
            menu.addAction(open_action)
            menu.addAction(open_new_action)
        elif item_type == "note":
            open_action = QAction("Open", self)
            open_action.triggered.connect(lambda: self.open_note_tab(data["id"]))
            menu.addAction(open_action)
        else:
            open_action = QAction("Open", self)
            open_action.triggered.connect(lambda: self.open_summary_tab(data))
            menu.addAction(open_action)

        menu.exec(self.history_list.viewport().mapToGlobal(point))

    def close_other_tabs(self, keep_index):
        # We need to be careful with indices shifting.
        # Strategy: Iterate backwards and close if index != keep_index
        count = self.central_tabs.count()
        for i in range(count - 1, -1, -1):
            if i != keep_index:
                self.close_tab(i)

    def close_all_tabs(self):
        count = self.central_tabs.count()
        for i in range(count - 1, -1, -1):
            self.close_tab(i)
        
        if self.central_tabs.count() == 0:
            self.show_welcome_screen()

    def load_history(self, tag_filter="All", favorites_only=False):
        self.history_list.clear()
        
        # Get current filter settings from UI if not provided
        if tag_filter == "All":
            tag_filter = self.tag_filter_combo.currentText()
        if not favorites_only:
            favorites_only = self.fav_filter_cb.isChecked()

        # 1. Fetch Recordings
        records = []
        tags_for_query = [tag_filter] if tag_filter != "All" else None

        if self.current_week_monday:
            # Range filtering (Monday to end of selection)
            start_date = self.current_week_monday.toString("yyyy-MM-dd")
            if self.current_date_filter:
                end_date = self.current_date_filter
            else:
                end_date = self.current_week_monday.addDays(6).toString("yyyy-MM-dd")
            records = self.db.fetch_by_date_range(start_date, end_date, tags_for_query, favorites_only=favorites_only)
        elif self.current_date_filter:
            # Specific day only (set via Ctrl+Click)
            records = self.db.fetch_by_date_range(self.current_date_filter, self.current_date_filter, tags_for_query, favorites_only=favorites_only)
        else:
            records = self.db.fetch_all(tag_filter=tag_filter, favorites_only=favorites_only)
            
        # 2. Combine with Summaries
        all_items = []
        for r in records:
            if 'type' not in r or not r['type']:
                r['type'] = 'recording'
            r['sort_date'] = r['created_at']
            all_items.append(r)
            
        if not favorites_only:
            tags_filter = tag_filter if tag_filter != "All" else None
            
            if self.current_week_monday:
                start_date = self.current_week_monday.toString("yyyy-MM-dd")
                if self.current_date_filter:
                    end_date = self.current_date_filter
                else:
                    end_date = self.current_week_monday.addDays(6).toString("yyyy-MM-dd")
                
                # Weekly Summary Context (Use Sunday as key)
                week_sunday = self.current_week_monday.addDays(6).toString("yyyy-MM-dd")
                weekly_summary = self.db.get_weekly_summary(week_sunday, tags_filter)
                if weekly_summary:
                    all_items.append({
                        'type': 'weekly',
                        'week_start': week_sunday,
                        'summary': weekly_summary,
                        'sort_date': week_sunday + " 23:59:59"
                    })
                
                # Daily Summaries for the range
                daily_sums = self.db.fetch_daily_summaries_by_range(start_date, end_date, tags_filter)
                for ds in daily_sums:
                    ds['type'] = 'daily'
                    ds['sort_date'] = ds['date'] + " 23:59:59"
                    all_items.append(ds)
            elif self.current_date_filter:
                # Specific day summary (Ctrl+Click)
                summary_text = self.db.get_daily_summary(self.current_date_filter, tags_filter)
                if summary_text:
                    all_items.append({
                        'type': 'daily',
                        'date': self.current_date_filter,
                        'tags_filter': tags_filter if tags_filter else '',
                        'summary': summary_text,
                        'sort_date': self.current_date_filter + " 23:59:59"
                    })
            else:
                # Fetch recent summaries as fallback when no filter
                daily_sums = self.db.fetch_daily_summaries(limit=20)
                for ds in daily_sums:
                    ds['type'] = 'daily'
                    ds['sort_date'] = ds['date'] + " 23:59:59"
                    all_items.append(ds)
                    
                weekly_sums = self.db.fetch_weekly_summaries(limit=5)
                for ws in weekly_sums:
                    ws['type'] = 'weekly'
                    ws['sort_date'] = ws['week_start'] + " 23:59:59"
                    all_items.append(ws)
        
        # 3. Sort and Display
        all_items.sort(key=lambda x: x['sort_date'], reverse=True)

        for item_data in all_items:
            item = QListWidgetItem(self.history_list)
            
            if item_data['type'] in ['recording', 'note']:
                widget = RecordingListItemWidget(item_data)
                widget.favorite_toggled.connect(lambda checked, r_id=item_data['id']: self.on_favorite_toggled(r_id, checked))
                widget.delete_requested.connect(lambda r_id=item_data['id']: self.delete_recording(r_id))
            else:
                widget = SummaryListItemWidget(item_data)
                
            item.setSizeHint(widget.sizeHint())
            self.history_list.addItem(item)
            self.history_list.setItemWidget(item, widget)
            item.setData(Qt.ItemDataRole.UserRole, item_data) # Store data for click handler
            
        # Re-apply search filter if any
        self.filter_history_list(self.search_input.text())
        
        # Refresh welcome screen lists if it exists
        if hasattr(self, 'welcome_widget') and self.welcome_widget:
            try:
                self.welcome_widget.load_favorites()
                self.welcome_widget.load_today()
            except Exception as e:
                print(f"Error refreshing welcome widget: {e}")

    def refresh_sidebar(self):
        """Manually refresh the history list and tags."""
        self.request_sidebar_reload(include_tags=True, include_history=True)

    def request_sidebar_reload(self, include_tags=False, include_history=True, delay_ms=120):
        self._pending_history_reload = self._pending_history_reload or include_history
        self._pending_tag_reload = self._pending_tag_reload or include_tags
        self._sidebar_refresh_timer.start(delay_ms)

    def _apply_pending_sidebar_reload(self):
        refresh_tags = self._pending_tag_reload
        refresh_history = self._pending_history_reload or refresh_tags
        self._pending_history_reload = False
        self._pending_tag_reload = False

        if refresh_tags:
            self.refresh_tag_filter()
        if refresh_history:
            self.load_history()
        self.refresh_tasks_sidebar()

    def refresh_tag_filter(self):
        current_tag = self.tag_filter_combo.currentText()
        self.tag_filter_combo.blockSignals(True)
        self.tag_filter_combo.clear()
        self.tag_filter_combo.addItem("All")
        
        if self.current_date_filter:
            # Fetch records for this date to get relevant tags
            records = self.db.fetch_by_date_range(self.current_date_filter, self.current_date_filter)
            tags = set()
            for r in records:
                if r['tags']:
                    tags.update([t.strip() for t in r['tags'].split(',') if t.strip()])
            sorted_tags = sorted(list(tags))
        else:
            sorted_tags = self.db.get_all_tags()
            
        self.tag_filter_combo.addItems(sorted_tags)
        
        index = self.tag_filter_combo.findText(current_tag)
        if index >= 0:
            self.tag_filter_combo.setCurrentIndex(index)
        else:
            self.tag_filter_combo.setCurrentIndex(0)
        self.tag_filter_combo.blockSignals(False)
        self.load_collections()

    def load_collections(self):
        if not hasattr(self, "collections_list"):
            return
        self.collections_list.clear()
        tags = self.db.get_all_tags()
        if not tags:
            self.collections_list.addItem("No tags.")
            return
        for tag in tags:
            item = QListWidgetItem(tag)
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.collections_list.addItem(item)

    def load_notebooks(self):
        """Load notebooks into the sidebar list."""
        self.notebooks_list.clear()
        notebooks = self.notebook_db.get_notebooks()
        for nb in notebooks[:5]:  # Show only first 5 in sidebar
            item = QListWidgetItem(f"📓 {nb['name']}")
            item.setData(Qt.ItemDataRole.UserRole, nb['id'])
            self.notebooks_list.addItem(item)

    def on_notebook_clicked(self, item):
        """Handle notebook click in sidebar."""
        notebook_id = item.data(Qt.ItemDataRole.UserRole)
        notebook_name = item.text().replace("📓 ", "")
        self.open_notebook(notebook_id, notebook_name)

    def on_collection_clicked(self, item):
        tag = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if not tag or tag == "No tags.":
            return
        self.open_collection_tab(tag)

    def create_notebook(self):
        name, ok = QInputDialog.getText(self, "New Notebook", "Notebook Name:")
        if ok and name.strip():
            self.notebook_db.create_notebook(name.strip())
            self.load_notebooks()

    def _find_notebook_by_id(self, notebook_id):
        notebooks = self.notebook_db.get_notebooks()
        return next((nb for nb in notebooks if nb.get("id") == notebook_id), None)

    def rename_notebook(self, notebook_id):
        notebook = self._find_notebook_by_id(notebook_id)
        if not notebook:
            return
        new_name, ok = QInputDialog.getText(self, "Rename Notebook", "New Name:", text=notebook["name"])
        if ok and new_name.strip():
            self.notebook_db.rename_notebook(notebook_id, new_name.strip())
            self.load_notebooks()

    def delete_notebook(self, notebook_id):
        notebook = self._find_notebook_by_id(notebook_id)
        if not notebook:
            return
        reply = QMessageBox.question(
            self,
            "Delete Notebook",
            f"Are you sure you want to delete '{notebook['name']}' and all its notes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.notebook_db.delete_notebook(notebook_id)
            self.load_notebooks()

    def show_notebooks_sidebar_context_menu(self, point):
        item = self.notebooks_list.itemAt(point)
        if not item:
            return

        notebook_id = item.data(Qt.ItemDataRole.UserRole)
        notebook_name = item.text().replace("📓 ", "")
        if not isinstance(notebook_id, int):
            return

        menu = QMenu(self)
        open_action = menu.addAction("Open")
        chat_action = menu.addAction("Chat")
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")

        chosen = menu.exec(self.notebooks_list.viewport().mapToGlobal(point))
        if chosen == open_action:
            self.open_notebook(notebook_id, notebook_name)
        elif chosen == chat_action:
            self.open_notebook_chat(notebook_id, notebook_name)
        elif chosen == rename_action:
            self.rename_notebook(notebook_id)
        elif chosen == delete_action:
            self.delete_notebook(notebook_id)

    def open_selected_tag_chat(self):
        item = self.collections_list.currentItem()
        if item is None:
            self.open_chat_tab(None)
            return

        tag = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if not tag or tag == "No tags.":
            self.open_chat_tab(None)
            return
        self.open_collection_chat(tag)

    def show_tags_sidebar_context_menu(self, point):
        item = self.collections_list.itemAt(point)
        if not item:
            return

        tag = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if not tag or tag == "No tags.":
            return

        menu = QMenu(self)
        open_action = menu.addAction("Open")
        chat_action = menu.addAction("Chat")

        chosen = menu.exec(self.collections_list.viewport().mapToGlobal(point))
        if chosen == open_action:
            self.open_collection_tab(tag)
        elif chosen == chat_action:
            self.open_collection_chat(tag)

    def open_collection_tab(self, tag):
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, CollectionWidget) and widget.tag == tag:
                self.central_tabs.setCurrentIndex(i)
                return

        col_widget = CollectionWidget(tag)
        col_widget.open_recording.connect(self.open_recording_tab)
        col_widget.start_chat.connect(self.open_collection_chat)
        
        index = self.central_tabs.addTab(col_widget, f"Collection: {tag}")
        self.central_tabs.setCurrentIndex(index)

    def open_collection_chat(self, tag):
        self.open_chat_tab(initial_contexts=[{"type": "tag", "value": tag, "label": tag}])

    def open_calendar_tab(self):
        # If already open, switch to it and sync
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, CalendarWidget):
                self.central_tabs.setCurrentIndex(i)
                widget.set_selection(self.current_week_monday, self.current_date_filter)
                return

        # Pass rag_engine (self) to the CalendarWidget
        tab = CalendarWidget(self, task_queue=self.summary_task_queue)
        tab.start_chat_requested.connect(self.open_chat_tab_with_filters)
        tab.selection_changed.connect(self.on_tab_selection_sync)
        
        # Set initial selection and tags
        tag = self.tag_filter_combo.currentText()
        tab.set_selection(self.current_week_monday, self.current_date_filter, tag if tag != "All" else None)
        
        index = self.central_tabs.addTab(tab, "Week Details")
        self.central_tabs.setCurrentIndex(index)

    def on_tag_filter_changed(self, tag):
        self.request_sidebar_reload(include_history=True)
        self.sync_active_tabs()

    def on_tab_selection_sync(self, monday, date_str, tag=None):
        """Update sidebar calendar state when user navigates inside the Week Details tab."""
        self.current_week_monday = monday if monday.isValid() else None
        self.current_date_filter = date_str
        
        # Update calendar widget without triggering signals
        self.calendar.blockSignals(True)
        if date_str:
            target = QDate.fromString(date_str, "yyyy-MM-dd")
            self.calendar.setSelectedDate(target)
        self.calendar.blockSignals(False)
        
        # Sync tags if provided
        if tag:
            idx = self.tag_filter_combo.findText(tag)
            if idx >= 0:
                self.tag_filter_combo.blockSignals(True)
                self.tag_filter_combo.setCurrentIndex(idx)
                self.tag_filter_combo.blockSignals(False)
        elif tag == "": # All
             self.tag_filter_combo.blockSignals(True)
             self.tag_filter_combo.setCurrentIndex(0)
             self.tag_filter_combo.blockSignals(False)

        self.update_calendar_visuals()
        self.request_sidebar_reload(include_tags=True, include_history=True)
        self.sync_active_tabs()



    def open_chat_tab_with_filters(self, date_str, tags):
        contexts = []
        if date_str:
            contexts.append({"type": "date", "value": date_str, "label": date_str})
        if tags:
            for tag in tags:
                contexts.append({"type": "tag", "value": tag, "label": tag})
        self.open_chat_tab(initial_contexts=contexts)

    def open_chat_with_contexts(self, contexts, floating=False):
        normalized = list(contexts or [])
        if floating:
            return self.open_floating_chat(initial_contexts=normalized)
        return self.open_chat_tab(initial_contexts=normalized)

    def on_history_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        type_ = data.get('type', 'recording')
        
        if type_ == 'recording':
            self.open_recording_tab(data['id'])
        elif type_ == 'note':
            self.open_note_tab(data['id'])
        else:
            self.open_summary_tab(data)

    def open_summary_tab(self, summary_data):
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, SummaryViewerWidget):
                # Compare content or ID to identify duplicate?
                # For summaries, we might use date/week_start + type as ID
                w_data = widget.summary_data
                if w_data.get('type') == summary_data.get('type'):
                    if (
                        w_data.get('type') == 'daily'
                        and w_data.get('date') == summary_data.get('date')
                        and (w_data.get('tags_filter') or '') == (summary_data.get('tags_filter') or '')
                    ):
                        self.central_tabs.setCurrentIndex(i)
                        return
                    if w_data.get('type') == 'weekly' and w_data.get('week_start') == summary_data.get('week_start'):
                        self.central_tabs.setCurrentIndex(i)
                        return

        viewer = SummaryViewerWidget(summary_data, db=self.db, task_queue=self.summary_task_queue)
        viewer.regenerate_requested.connect(self.regenerate_summary)
        viewer.open_recording_requested.connect(self.open_recording_tab)
        viewer.start_chat_requested.connect(self.open_chat_tab_with_filters)
        viewer.start_chat_contexts_requested.connect(self.open_chat_with_contexts)
        # viewer.close_requested.connect(...) # If we added a close signal
        
        type_ = summary_data.get('type')
        title = f"📅 {summary_data.get('date')}" if type_ == 'daily' else f"📅 Week ending {summary_data.get('week_start')}"
        
        index = self.central_tabs.addTab(viewer, title)
        self.central_tabs.setCurrentIndex(index)

    def regenerate_summary(self, summary_data):
        date = summary_data.get('date')
        if not date:
            return
        payload = dict(summary_data or {})
        payload.setdefault("source", "welcome")
        self.summary_task_queue.enqueue_daily_summary(payload)



    def perform_welcome_search(self, query):
        if not self.rag:
            QMessageBox.warning(self, "RAG Error", "RAG Engine not initialized.")
            return
            
        if not query:
            return
            
        if self.search_thread and self.search_thread.isRunning():
            return
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        
        # Reuse SearchThread
        self.search_thread = SearchThread(self.rag, query)
        self.search_thread.finished.connect(lambda results: self.on_search_finished_new_tab(results, query))
        self.search_thread.error.connect(self.on_search_error)
        self.search_thread.start()

    def on_search_finished_new_tab(self, results, query):
        QApplication.restoreOverrideCursor()
        self.search_thread = None
        
        # Create Search Results Widget
        search_widget = SearchResultsWidget(query)
        search_widget.display_results(results)
        search_widget.result_clicked.connect(self.open_recording_tab)
        
        # Add to tabs
        index = self.central_tabs.addTab(search_widget, f"Search: {query}")
        self.central_tabs.setCurrentIndex(index)

    def on_search_error(self, error_message):
        QApplication.restoreOverrideCursor()
        self.search_thread = None
        QMessageBox.critical(self, "Search Error", f"An error occurred during search: {error_message}")

    def load_chat_sessions(self):
        self.sessions_list.clear()
        sessions = self.db.fetch_chat_sessions()
        for s in sessions:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, s)
            self.sessions_list.addItem(item)
            widget = SidebarChatSessionWidget(s, parent=self.sessions_list)
            widget.expand_requested.connect(lambda _session_id=None: self.open_chat_history_tab())
            item.setSizeHint(widget.sizeHint())
            self.sessions_list.setItemWidget(item, widget)
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, ChatHistoryWidget):
                widget.set_sessions(sessions)

    def refresh_tasks_sidebar(self):
        if not hasattr(self, "tasks_sidebar_list"):
            return

        self.tasks_sidebar_list.blockSignals(True)
        self.tasks_sidebar_list.clear()
        tag = self.tag_filter_combo.currentText() if hasattr(self, "tag_filter_combo") else "All"
        tags_filter = tag if tag and tag != "All" else None

        if self.current_week_monday and self.current_date_filter:
            tasks = self.db.get_tasks_by_date_range(
                self.current_week_monday.toString("yyyy-MM-dd"),
                self.current_date_filter,
                tags_filter=tags_filter,
                include_completed=False,
            )
            if self.tasks_sidebar_limit is not None:
                tasks = tasks[:self.tasks_sidebar_limit]
        elif self.current_date_filter:
            tasks = self.db.get_tasks_by_date(
                self.current_date_filter,
                tags_filter=tags_filter,
            )
            tasks = [task for task in tasks if not bool(task.get("is_completed"))]
            if self.tasks_sidebar_limit is not None:
                tasks = tasks[:self.tasks_sidebar_limit]
        else:
            tasks = self.db.get_recent_incomplete_tasks(limit=self.tasks_sidebar_limit)

        if not tasks:
            self.tasks_sidebar_list.addItem("No incomplete tasks.")
            self.tasks_sidebar_list.blockSignals(False)
            return

        for task in tasks:
            if isinstance(task.get("record_id"), int):
                tags = (task.get("record_tags") or task.get("tags") or "").strip()
            else:
                tags = (task.get("tags") or task.get("record_tags") or "").strip()
            content = (task.get("content") or "").strip() or "Untitled task"
            if len(content) > 72:
                content = content[:69].rstrip() + "..."

            tag_values = [t.strip() for t in tags.split(",") if t.strip()]

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task)
            self.tasks_sidebar_list.addItem(item)
            widget = SidebarTaskCompactWidget(
                content,
                tag_values,
                task_id=task.get("id"),
                is_completed=bool(task.get("is_completed")),
                parent=self.tasks_sidebar_list,
            )
            widget.completion_toggled.connect(self._toggle_sidebar_task_completion)
            item.setSizeHint(widget.sizeHint())
            self.tasks_sidebar_list.setItemWidget(item, widget)
        
        # Connect signal if not already connected (though it's safer to check)
        try:
            self.tasks_sidebar_list.itemChanged.disconnect(self.on_task_sidebar_item_changed)
        except:
            pass
        self.tasks_sidebar_list.itemChanged.connect(self.on_task_sidebar_item_changed)
        self.tasks_sidebar_list.blockSignals(False)

    def _toggle_sidebar_task_completion(self, task_id, is_completed):
        if not isinstance(task_id, int):
            return
        self.db.toggle_task_completion(task_id, bool(is_completed))
        self.refresh_tasks_sidebar()

    def on_task_sidebar_item_changed(self, item):
        task = item.data(Qt.ItemDataRole.UserRole)
        if not task:
            return
            
        is_completed = item.checkState() == Qt.CheckState.Checked
        self.db.toggle_task_completion(task['id'], is_completed)
        
        # Apply visual feedback (strikethrough)
        font = item.font()
        font.setStrikeOut(is_completed)
        item.setFont(font)
        if is_completed:
            item.setForeground(Qt.GlobalColor.gray)
        else:
            # Revert to default color (theme dependent)
            item.setForeground(QApplication.palette().text())
        
        # We DON'T refresh immediately here, so the user can see it's checked.
        # It will disappear on next regular refresh.

    def show_tasks_sidebar_context_menu(self, point):
        item = self.tasks_sidebar_list.itemAt(point)
        if not item:
            return
        task = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            return

        menu = QMenu(self)
        is_completed = bool(task.get("is_completed"))
        complete_action = menu.addAction("Mark as pending" if is_completed else "Mark as completed")
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        go_action = menu.addAction("Go to recording")
        go_action.setEnabled(isinstance(task.get("record_id"), int))

        chosen = menu.exec(self.tasks_sidebar_list.viewport().mapToGlobal(point))
        if chosen is None:
            return
        if chosen == complete_action:
            self.db.toggle_task_completion(task["id"], not is_completed)
            self.refresh_tasks_sidebar()
        elif chosen == edit_action:
            dialog = TaskEditDialog(self.db, self, title="Edit Task", task_data=task)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.db.update_task_details(
                    task["id"],
                    dialog.get_content(),
                    dialog.get_notes(),
                    dialog.get_tags(),
                )
                self.refresh_tasks_sidebar()
        elif chosen == delete_action:
            if QMessageBox.question(self, "Delete Task", "Delete this task?") == QMessageBox.StandardButton.Yes:
                self.db.delete_task(task["id"])
                self.refresh_tasks_sidebar()
        elif chosen == go_action and isinstance(task.get("record_id"), int):
            self.open_recording_tab(task["record_id"])

    def on_chat_session_clicked(self, item):
        session = item.data(Qt.ItemDataRole.UserRole)
        self.open_chat_tab(session['id'])

    def show_chat_sidebar_context_menu(self, point):
        item = self.sessions_list.itemAt(point)
        if not item:
            return

        session = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(session, dict):
            return

        menu = QMenu(self)
        open_action = menu.addAction("Open")
        open_floating_action = menu.addAction("Open Floating")
        delete_action = menu.addAction("Delete")

        chosen = menu.exec(self.sessions_list.viewport().mapToGlobal(point))
        if chosen == open_action:
            self.open_chat_tab(session["id"])
        elif chosen == open_floating_action:
            self.open_floating_chat(session["id"])
        elif chosen == delete_action:
            self.delete_chat_session_by_id(session["id"])

    def delete_chat_session_by_id(self, session_id):
        sessions = self.db.fetch_chat_sessions()
        session = next((s for s in sessions if s.get("id") == session_id), None)
        if not session:
            return

        reply = QMessageBox.question(
            self,
            "Delete Chat",
            f"Are you sure you want to delete '{session['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.db.delete_chat_session(session["id"])
        self.load_chat_sessions()

        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, ChatWidget) and widget.current_session_id == session["id"]:
                self.central_tabs.removeTab(i)
                widget.deleteLater()
                break
        floating_host = self._find_floating_chat_host(session["id"])
        if floating_host is not None:
            widget = floating_host.property("chat_widget")
            if isinstance(widget, ChatWidget):
                widget.setParent(None)
            self._remove_floating_host(floating_host)
            if isinstance(widget, ChatWidget):
                widget.deleteLater()
        self._sync_chat_context_section()

    def delete_selected_chat_session(self):
        item = self.sessions_list.currentItem()
        if not item:
            return
        session = item.data(Qt.ItemDataRole.UserRole)
        self.delete_chat_session_by_id(session["id"])

    def on_calendar_date_changed(self):
        date = self.calendar.selectedDate()
        modifiers = QApplication.keyboardModifiers()
        
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Ctrl-click: select specific day ONLY
            self.current_date_filter = date.toString("yyyy-MM-dd")
            self.current_week_monday = None
        else:
            # Normal click: progressive filter [Monday, SelectedDay]
            day_of_week = date.dayOfWeek()
            self.current_week_monday = date.addDays(-(day_of_week - 1))
            self.current_date_filter = date.toString("yyyy-MM-dd")
            
        self.update_calendar_visuals()
        self.request_sidebar_reload(include_tags=True, include_history=True)
        self.sync_active_tabs()

    def sync_active_tabs(self):
        """Push current sidebar selection and tags to active tabs (Calendar, Chat)."""
        tag = self.tag_filter_combo.currentText()
        tags_filter = tag if tag != "All" else None
        
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, CalendarWidget):
                widget.set_selection(self.current_week_monday, self.current_date_filter, tags_filter)
            elif isinstance(widget, ChatWidget):
                widget.update_from_global_selection(self.current_week_monday, self.current_date_filter, tags_filter or "")
            elif isinstance(widget, TasksListWidget):
                widget.set_global_filters(self.current_week_monday, self.current_date_filter, tags_filter)
        for host in self.floating_chat_hosts:
            widget = host.property("chat_widget")
            if isinstance(widget, ChatWidget):
                widget.update_from_global_selection(self.current_week_monday, self.current_date_filter, tags_filter or "")

    def prev_week_sidebar(self):
        """Move to previous week, showing full week by default (selecting Sunday)."""
        if not self.current_week_monday:
            dt = self.calendar.selectedDate()
            self.current_week_monday = dt.addDays(-(dt.dayOfWeek() - 1))
            
        self.current_week_monday = self.current_week_monday.addDays(-7)
        # Select Sunday of that week to show full range
        sunday = self.current_week_monday.addDays(6)
        self.current_date_filter = sunday.toString("yyyy-MM-dd")
        
        # Update calendar view
        self.calendar.setSelectedDate(sunday)
        self.update_calendar_visuals()
        self.request_sidebar_reload(include_tags=True, include_history=True)

    def next_week_sidebar(self):
        """Move to next week, showing full week by default (selecting Sunday)."""
        if not self.current_week_monday:
            dt = self.calendar.selectedDate()
            self.current_week_monday = dt.addDays(-(dt.dayOfWeek() - 1))
            
        self.current_week_monday = self.current_week_monday.addDays(7)
        # Select Sunday of that week to show full range
        sunday = self.current_week_monday.addDays(6)
        self.current_date_filter = sunday.toString("yyyy-MM-dd")
        
        # Update calendar view
        self.calendar.setSelectedDate(sunday)
        self.update_calendar_visuals()
        self.request_sidebar_reload(include_tags=True, include_history=True)
        
    def update_calendar_visuals(self):
        """Highlight full week context and active progressive range."""
        reset_fmt = QTextCharFormat()
        
        week_fmt = QTextCharFormat()
        week_fmt.setBackground(QColor("#E3F2FD"))
        
        selected_fmt = QTextCharFormat()
        selected_fmt.setBackground(QColor("#2196F3"))
        selected_fmt.setForeground(QColor("white"))

        if hasattr(self, '_last_highlighted_dates'):
            for d in self._last_highlighted_dates:
                self.calendar.setDateTextFormat(d, reset_fmt)
        
        highlighted = []
        
        # 1. Full Week Highlight (Context)
        if self.current_week_monday:
            mon = self.current_week_monday
            for i in range(7):
                d = mon.addDays(i)
                self.calendar.setDateTextFormat(d, week_fmt)
                highlighted.append(d)
                
            # 2. Active Range Highlight (Overwrites if in progressive or specific mode)
            if self.current_date_filter:
                end_date = QDate.fromString(self.current_date_filter, "yyyy-MM-dd")
                
                if mon and end_date >= mon and end_date <= mon.addDays(6):
                    # Progressive: Mon to end_date
                    curr = mon
                    while curr <= end_date:
                        self.calendar.setDateTextFormat(curr, selected_fmt)
                        if curr not in highlighted: highlighted.append(curr)
                        curr = curr.addDays(1)
                else:
                    # Specific Day Only (Ctrl+Click Case where week context might be different or missing)
                    self.calendar.setDateTextFormat(end_date, selected_fmt)
                    if end_date not in highlighted: highlighted.append(end_date)
            else:
                # Nav buttons case: No final day filter, show full week as selected?
                # The user said "avanzar/retroceder semana que mueva entrre semanas sin dia en concreto"
                # Let's highlight full week in Dark Blue when using buttons.
                for i in range(7):
                    d = mon.addDays(i)
                    self.calendar.setDateTextFormat(d, selected_fmt)
                    if d not in highlighted: highlighted.append(d)
        elif self.current_date_filter:
            # Specific Day Fallback
            d = QDate.fromString(self.current_date_filter, "yyyy-MM-dd")
            self.calendar.setDateTextFormat(d, selected_fmt)
            highlighted.append(d)
        
        self._last_highlighted_dates = highlighted

    def reset_date_filter(self):
        self.current_date_filter = None
        self.current_week_monday = None
        self.update_calendar_visuals()
        self.request_sidebar_reload(include_tags=True, include_history=True)

    def filter_history_list(self, text):
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            record = item.data(Qt.ItemDataRole.UserRole)
            title = record.get('title', '') or ''
            date = record.get('created_at', '') or ''
            
            if not text or text.lower() in title.lower() or text.lower() in date.lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def on_favorite_toggled(self, record_id, is_favorite):
        self.db.toggle_favorite(record_id, is_favorite)
        # No need to reload list, button state is already updated locally
        
    def delete_recording(self, record_id):
        reply = QMessageBox.question(self, "Delete Recording", 
                                   "Are you sure you want to delete this recording? This cannot be undone.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            logging.info("delete_recording requested for record_id=%s", record_id)
            filename = self.db.delete(record_id)
            
            # Delete file
            if filename:
                try:
                    file_path = os.path.join(os.getcwd(), "recordings", filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting file {filename}: {e}")
            
            # Delete from RAG
            if self.rag:
                try:
                    logging.info("delete_recording: deleting record_id=%s from RAG", record_id)
                    self.rag.delete_document(str(record_id))
                except Exception as e:
                    print(f"Error deleting from RAG: {e}")
            
            self.load_history()
            self._close_recording_tabs(record_id)

    def open_settings_tab(self):
        """Open settings as a tab."""
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, SettingsWidget):
                self.central_tabs.setCurrentIndex(i)
                return

        settings_widget = SettingsWidget()
        settings_widget.rag_initialize_requested.connect(
            lambda cfg: self._build_rag_engine(cfg, reason="initialize")
        )
        settings_widget.rag_reload_requested.connect(
            lambda cfg: self._build_rag_engine(cfg, reason="reload")
        )
        settings_widget.rag_reindex_requested.connect(
            lambda: self.summary_task_queue.enqueue_rag_reindex(source="settings")
        )
        index = self.central_tabs.addTab(settings_widget, "Settings")
        self.central_tabs.setCurrentIndex(index)

    def import_audio_file(self, config):
        """Import an audio file with the given transcription configuration."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Audio", "", "Audio Files (*.wav *.mp3 *.m4a *.ogg *.flac);;All Files (*)")
        if not file_path:
            return

        try:
            # 1. Copy file to recordings dir
            filename = os.path.basename(file_path)
            dest_path = os.path.join(os.getcwd(), "recordings", filename)
            
            # Handle duplicate filenames
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(dest_path):
                    new_filename = f"{base}_{i}{ext}"
                    dest_path = os.path.join(os.getcwd(), "recordings", new_filename)
                    i += 1
                filename = os.path.basename(dest_path)

            shutil.copy2(file_path, dest_path)

            # 2. Create DB entry
            record_id = self.db.save(filename, "", 0.0, title=filename)
            
            # 3. Open Recording Tab with config
            rec_widget = self.open_recording_tab(record_id, config)
            
            # 4. Trigger Transcription with config
            if rec_widget and isinstance(rec_widget, RecordingWidget):
                rec_widget.start_transcription_with_config(dest_path, config)

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import audio: {e}")

    def open_collections_list(self):
        """Open a tab showing all collections."""
        # Check if already open
        for i in range(self.central_tabs.count()):
            tab_text = self.central_tabs.tabText(i)
            if tab_text == "Colecciones":
                self.central_tabs.setCurrentIndex(i)
                return
        
        # Create a simple widget listing all collections
        from PyQt6.QtWidgets import QScrollArea
        
        collections_widget = QWidget()
        layout = QVBoxLayout(collections_widget)
        layout.setSpacing(10)
        
        title = QLabel("<h2>🏷️ Todas las Colecciones</h2>")
        layout.addWidget(title)
        
        tags = self.db.get_all_tags()
        
        if not tags:
            layout.addWidget(QLabel("No hay colecciones aún. Añade tags a tus grabaciones."))
        else:
            list_widget = QListWidget()
            list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            # list_widget.setStyleSheet(LIST_WIDGET_STYLE)
            for tag in tags:
                item = QListWidgetItem(f"🏷️ {tag}")
                item.setData(Qt.ItemDataRole.UserRole, tag)
                list_widget.addItem(item)
            list_widget.itemClicked.connect(lambda item: self.open_collection_tab(item.data(Qt.ItemDataRole.UserRole)))
            layout.addWidget(list_widget)
        
        layout.addStretch()
        
        index = self.central_tabs.addTab(collections_widget, "Colecciones")
        self.central_tabs.setCurrentIndex(index)

    def open_notebooks_list(self):
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, NotebooksListWidget):
                self.central_tabs.setCurrentIndex(i)
                return

        nb_list = NotebooksListWidget(self.notebook_db)
        nb_list.notebook_opened.connect(self.open_notebook)
        nb_list.chat_requested.connect(self.open_notebook_chat)
        
        index = self.central_tabs.addTab(nb_list, "Libretas")
        self.central_tabs.setCurrentIndex(index)

    def open_notebook(self, notebook_id, name):
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, NotebookWidget) and widget.notebook_id == notebook_id:
                self.central_tabs.setCurrentIndex(i)
                return

        nb_widget = NotebookWidget(self.notebook_db, notebook_id, name, self.recorder)
        nb_widget.chat_requested.connect(self.open_notebook_chat)
        
        index = self.central_tabs.addTab(nb_widget, f"📓 {name}")
        self.central_tabs.setCurrentIndex(index)

    def open_notebook_chat(self, notebook_id, notebook_name):
        # Check if already open
        # We can try to find a chat with this notebook as context
        # But for now, let's just open a new one or rely on user to manage
        
        self.open_chat_tab(initial_contexts=[{"type": "notebook", "value": notebook_id, "label": notebook_name}])

    # open_maintenance_tab removed - now handled by open_tools_tab

    def closeEvent(self, event):
        logging.warning(
            "MainWindow.closeEvent triggered. tabs=%d queue_running=%s recorder_recording=%s",
            self.central_tabs.count(),
            self.summary_task_queue.is_running if self.summary_task_queue else None,
            self.recorder.is_recording if self.recorder else None,
        )
        self._sidebar_refresh_timer.stop()
        self._pending_history_reload = False
        self._pending_tag_reload = False

        # Stop background workers before Qt starts tearing down widgets.
        if self.search_thread and self.search_thread.isRunning():
            try:
                self.search_thread.requestInterruption()
                self.search_thread.quit()
                self.search_thread.wait(3000)
            except Exception:
                pass
        self.search_thread = None

        if self.summary_task_queue:
            self.summary_task_queue.cancel_all()
            logging.info("Summary task queue cancelled during closeEvent.")
        self.regen_worker = None

        # Close tabs from right to left and allow each widget to cleanup resources.
        for i in range(self.central_tabs.count() - 1, -1, -1):
            widget = self.central_tabs.widget(i)
            if widget and hasattr(widget, "cleanup"):
                try:
                    widget.cleanup()
                except Exception:
                    pass
        for host in list(self.floating_chat_hosts):
            widget = host.property("chat_widget")
            if widget and hasattr(widget, "cleanup"):
                try:
                    widget.cleanup()
                except Exception:
                    pass
            self._remove_floating_host(host)

        if self.recorder and self.recorder.is_recording:
            try:
                self.recorder.stop()
                logging.info("Active recorder stopped during closeEvent.")
            except Exception:
                logging.exception("Failed stopping recorder during closeEvent.")

        try:
            import gc
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_floating_chat_bar()
        logging.warning("MainWindow.closeEvent completed.")
