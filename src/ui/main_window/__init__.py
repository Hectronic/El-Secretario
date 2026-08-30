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
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QPushButton, QToolButton,
                             QLabel, QMessageBox, QComboBox,
                             QTabWidget, QSplitter, QApplication, QStyle, QLineEdit,
                             QCalendarWidget, QCheckBox,
                             QFrame)
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QIcon

from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.ui.welcome_widget import WelcomeWidget
from src.ui.recording_widget import RecordingWidget
from src.ui.main_window.recording_tabs import RecordingTabCoordinator
from src.ui.main_window.bootstrap import bootstrap_main_window
from src.ui.main_window.content_tabs import ContentTabCoordinator
from src.ui.main_window.chat_floating import FloatingChatCoordinator
from src.ui.main_window.sidebar_sync import SidebarSyncCoordinator
from src.ui.main_window.chat_context_sidebar import install_chat_context_sidebar_section
from src.ui.main_window.sidebar_content import SidebarContentCoordinator
from src.ui.main_window.sidebar_actions import SidebarActionsCoordinator
from src.ui.main_window.setup_actions import SetupActionsCoordinator
from src.ui.main_window.tab_lifecycle import TabLifecycleCoordinator
from src.ui.main_window.search_actions import SearchActionsCoordinator
from src.ui.main_window.selection_sync_actions import SelectionSyncActionsCoordinator
from src.ui.main_window.history_navigation_actions import HistoryNavigationActionsCoordinator
from src.ui.main_window.summary_actions import SummaryActionsCoordinator
from src.ui.main_window.summary_queue_status import SummaryQueueStatusCoordinator
from src.ui.main_window.runtime_startup import RuntimeStartupCoordinator
from src.ui.recording_in_progress_widget import RecordingInProgressWidget
from src.ui.chat_widget import ChatWidget
from src.ui.calendar_widget import CalendarWidget
from src.ui.styles import LIST_WIDGET_STYLE, NEW_CHAT_BUTTON_STYLE, apply_theme

from src.ui.summary_task_queue import SummaryTaskQueueManager

Recorder = None

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
        self.recording_tabs = RecordingTabCoordinator(self)
        self.content_tabs = ContentTabCoordinator(self)
        self.sidebar_sync = SidebarSyncCoordinator(self)
        self.chat_floating = FloatingChatCoordinator(self)
        self.sidebar_content = SidebarContentCoordinator(self)
        self.sidebar_actions = SidebarActionsCoordinator(self)
        self.setup_actions = SetupActionsCoordinator(self)
        self.tab_lifecycle = TabLifecycleCoordinator(self)
        self.search_actions = SearchActionsCoordinator(self)
        self.selection_sync_actions = SelectionSyncActionsCoordinator(self)
        self.history_navigation_actions = HistoryNavigationActionsCoordinator(self)
        self.summary_actions = SummaryActionsCoordinator(self)
        self.summary_queue_status = SummaryQueueStatusCoordinator(self)
        self.runtime_startup = RuntimeStartupCoordinator(self)
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
        bootstrap_main_window(self)
        logging.info("MainWindow initialized.")

    def _apply_rag_runtime_env(self, rag_config):
        self.runtime_startup.apply_rag_runtime_env(rag_config)

    def _propagate_rag_engine_to_open_tabs(self):
        self.runtime_startup.propagate_rag_engine_to_open_tabs()

    def _build_rag_engine(self, rag_config, reason="runtime"):
        self.runtime_startup.build_rag_engine(rag_config, reason)

    def _log_user_settings_snapshot(self, context: str):
        self.runtime_startup.log_user_settings_snapshot(context)

    def _enqueue_missing_previous_week_summary_if_enabled(self):
        self.runtime_startup.enqueue_missing_previous_week_summary_if_enabled()

    def _enqueue_missing_previous_daily_summary_if_enabled(self):
        self.runtime_startup.enqueue_missing_previous_daily_summary_if_enabled()

    def _get_summary_queue_status(self):
        """Return the queue-status coordinator, including during early startup."""
        coordinator = self.__dict__.get("summary_queue_status")
        if coordinator is None:
            coordinator = SummaryQueueStatusCoordinator(self)
            self.__dict__["summary_queue_status"] = coordinator
        return coordinator

    def _setup_task_status_bar(self):
        self._get_summary_queue_status().setup_status_bar()

    def open_queue_manager_tab(self):
        self._get_summary_queue_status().open_queue_manager_tab()

    def _connect_task_queue_signals(self):
        self._get_summary_queue_status().connect_task_queue_signals()

    def _refresh_task_metrics(self):
        self._get_summary_queue_status().refresh_task_metrics()

    def _format_task_name(self, task):
        return self._get_summary_queue_status().format_task_name(task)

    def _on_summary_task_enqueued(self, task, position):
        self._get_summary_queue_status().on_summary_task_enqueued(task, position)

    def _on_summary_task_started(self, task, remaining_pending):
        self._get_summary_queue_status().on_summary_task_started(task, remaining_pending)

    def _on_summary_task_finished(self, task):
        self._get_summary_queue_status().on_summary_task_finished(task)

    def _on_summary_task_failed(self, task, error_msg):
        self._get_summary_queue_status().on_summary_task_failed(task, error_msg)

    def _on_summary_task_skipped(self, task, reason):
        self._get_summary_queue_status().on_summary_task_skipped(task, reason)

    def _on_summary_queue_changed(self, pending_count, is_running):
        self._get_summary_queue_status().on_summary_queue_changed(pending_count, is_running)

    def handle_status_message(self, message):
        self._get_summary_queue_status().handle_status_message(message)

    def handle_progress(self, value):
        self._get_summary_queue_status().handle_progress(value)

    def _refresh_daily_summary_viewers(self, date, tags_filter):
        self._get_summary_queue_status().refresh_daily_summary_viewers(date, tags_filter)

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
        install_chat_context_sidebar_section(
            self,
            right_panel=right_panel,
            right_layout=right_layout,
            create_section=create_section,
        )

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

        self.runtime_startup.initialize_rag_from_settings()

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

    def _sync_chat_context_section(self, chat_widget=None):
        self.sidebar_sync.sync_chat_context_section(chat_widget)

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
        return self.content_tabs.open_item_tab(record_id)

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

    def _sync_recording_tab_titles(self, record_id):
        self.recording_tabs.sync_recording_tab_titles(record_id)

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
        self.recording_tabs.close_recording_tabs(record_id)

    def open_recording_tab(self, record_id, config=None, force_new=False):
        """Open a recording tab for an existing record."""
        return self.recording_tabs.open_recording_tab(record_id, config=config, force_new=force_new)

    def open_recording_editor_tab(self, record_id, config=None):
        """Open a dedicated audio-editing tab for an existing recording."""
        return self.recording_tabs.open_recording_editor_tab(record_id, config=config)

    def open_note_tab(self, record_id=None):
        return self.content_tabs.open_note_tab(record_id)

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



    def changeEvent(self, event):
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.StyleChange,
        ) and hasattr(self, "floating_chat_bar"):
            self.chat_floating.refresh_floating_chat_bar()
        super().changeEvent(event)

    def _connect_chat_widget(self, chat_widget):
        self.chat_floating.connect_chat_widget(chat_widget)

    def _find_chat_tab_index(self, session_id):
        return self.chat_floating.find_chat_tab_index(session_id)

    def _find_floating_chat_host(self, session_id):
        return self.chat_floating.find_floating_chat_host(session_id)

    def _find_floating_chat_host_by_widget(self, chat_widget):
        return self.chat_floating.find_floating_chat_host_by_widget(chat_widget)

    def _remove_floating_host(self, host):
        self.chat_floating.remove_floating_host(host)

    def _refresh_floating_chat_bar(self):
        self.chat_floating.refresh_floating_chat_bar()

    def _tab_title_for_chat(self, chat_widget):
        return self.chat_floating.tab_title_for_chat(chat_widget)

    def _set_tab_action_buttons(self, widget):
        self.chat_floating.set_tab_action_buttons(widget)

    def _sync_chat_widget_title(self, chat_widget, title):
        self.chat_floating.sync_chat_widget_title(chat_widget, title)

    def float_chat_widget(self, chat_widget):
        self.chat_floating.float_chat_widget(chat_widget)

    def minimize_floating_chat(self, chat_widget):
        self.chat_floating.minimize_floating_chat(chat_widget)

    def restore_floating_chat(self, chat_widget):
        self.chat_floating.restore_floating_chat(chat_widget)

    def dock_chat_widget_to_tab(self, chat_widget):
        self.chat_floating.dock_chat_widget_to_tab(chat_widget)

    def close_chat_widget(self, chat_widget):
        self.chat_floating.close_chat_widget(chat_widget)

    def open_chat_tab(self, session_id=None, initial_contexts=None):
        return self.content_tabs.open_chat_tab(session_id=session_id, initial_contexts=initial_contexts)

    def open_floating_chat(self, session_id=None, initial_contexts=None):
        return self.content_tabs.open_floating_chat(session_id=session_id, initial_contexts=initial_contexts)

    def open_chat_tab_from_current_context(self):
        return self.content_tabs.open_chat_tab_from_current_context()

    def open_chat_history_tab(self):
        return self.content_tabs.open_chat_history_tab()

    def open_tools_tab(self, tab_index=0):
        return self.content_tabs.open_tools_tab(tab_index=tab_index)

    def open_tasks_tab(self, create_new=False):
        return self.content_tabs.open_tasks_tab(create_new=create_new)

    def close_tab(self, index):
        return self.tab_lifecycle.close_tab(index)

    def close_floating_chat(self, chat_widget):
        self.chat_floating.close_floating_chat(chat_widget)

    def show_tab_context_menu(self, point):
        return self.tab_lifecycle.show_tab_context_menu(point)

    def show_history_item_context_menu(self, point):
        return self.sidebar_actions.show_history_item_context_menu(point)

    def close_other_tabs(self, keep_index):
        return self.tab_lifecycle.close_other_tabs(keep_index)

    def close_all_tabs(self):
        return self.tab_lifecycle.close_all_tabs()

    def load_history(self, tag_filter="All", favorites_only=False):
        self.sidebar_content.load_history(tag_filter=tag_filter, favorites_only=favorites_only)

    def refresh_sidebar(self):
        self.sidebar_content.refresh_sidebar()

    def request_sidebar_reload(self, include_tags=False, include_history=True, delay_ms=120):
        self.sidebar_content.request_sidebar_reload(
            include_tags=include_tags,
            include_history=include_history,
            delay_ms=delay_ms,
        )

    def _apply_pending_sidebar_reload(self):
        self.sidebar_content._apply_pending_sidebar_reload()

    def refresh_tag_filter(self):
        self.sidebar_content.refresh_tag_filter()

    def load_collections(self):
        self.sidebar_content.load_collections()

    def load_notebooks(self):
        self.sidebar_content.load_notebooks()

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
        self.sidebar_content.create_notebook()

    def rename_notebook(self, notebook_id):
        self.sidebar_content.rename_notebook(notebook_id)

    def delete_notebook(self, notebook_id):
        self.sidebar_content.delete_notebook(notebook_id)

    def show_notebooks_sidebar_context_menu(self, point):
        self.sidebar_content.show_notebooks_sidebar_context_menu(point)

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
        return self.sidebar_actions.show_tags_sidebar_context_menu(point)

    def open_collection_tab(self, tag):
        return self.content_tabs.open_collection_tab(tag)

    def open_collection_chat(self, tag):
        self.open_chat_tab(initial_contexts=[{"type": "tag", "value": tag, "label": tag}])

    def open_calendar_tab(self):
        return self.content_tabs.open_calendar_tab()

    def on_tag_filter_changed(self, tag):
        self.request_sidebar_reload(include_history=True)
        self.sync_active_tabs()

    def on_tab_selection_sync(self, monday, date_str, tag=None):
        return self.selection_sync_actions.on_tab_selection_sync(monday, date_str, tag=tag)



    def open_chat_tab_with_filters(self, date_str, tags):
        return self.content_tabs.open_chat_tab_with_filters(date_str, tags)

    def open_chat_with_contexts(self, contexts, floating=False):
        return self.content_tabs.open_chat_with_contexts(contexts, floating=floating)

    def on_history_item_clicked(self, item):
        self.history_navigation_actions.on_history_item_clicked(item)

    def open_summary_tab(self, summary_data):
        return self.content_tabs.open_summary_tab(summary_data)

    def regenerate_summary(self, summary_data):
        self.summary_actions.regenerate_summary(summary_data)



    def perform_welcome_search(self, query):
        self.search_actions.perform_welcome_search(query)

    def on_search_finished_new_tab(self, results, query):
        self.search_actions.on_search_finished_new_tab(results, query)

    def on_search_error(self, error_message):
        self.search_actions.on_search_error(error_message)

    def load_chat_sessions(self):
        self.sidebar_content.load_chat_sessions()

    def refresh_tasks_sidebar(self):
        self.sidebar_actions.refresh_tasks_sidebar()

    def on_task_sidebar_item_changed(self, item):
        self.sidebar_actions.on_task_sidebar_item_changed(item)

    def show_tasks_sidebar_context_menu(self, point):
        self.sidebar_actions.show_tasks_sidebar_context_menu(point)

    def on_chat_session_clicked(self, item):
        self.sidebar_actions.on_chat_session_clicked(item)

    def show_chat_sidebar_context_menu(self, point):
        self.sidebar_actions.show_chat_sidebar_context_menu(point)

    def delete_chat_session_by_id(self, session_id):
        self.sidebar_actions.delete_chat_session_by_id(session_id)

    def delete_selected_chat_session(self):
        self.sidebar_actions.delete_selected_chat_session()

    def on_calendar_date_changed(self):
        self.sidebar_actions.on_calendar_date_changed()

    def sync_active_tabs(self):
        self.sidebar_actions.sync_active_tabs()

    def prev_week_sidebar(self):
        self.sidebar_actions.prev_week_sidebar()

    def next_week_sidebar(self):
        self.sidebar_actions.next_week_sidebar()

    def update_calendar_visuals(self):
        self.sidebar_actions.update_calendar_visuals()

    def reset_date_filter(self):
        self.sidebar_actions.reset_date_filter()

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
                except Exception:
                    logging.exception("Error deleting recording file %s", filename)

            # Delete from RAG
            if self.rag:
                try:
                    logging.info("delete_recording: deleting record_id=%s from RAG", record_id)
                    self.rag.delete_document(str(record_id))
                except Exception:
                    logging.exception("Error deleting record_id=%s from RAG", record_id)

            self.load_history()
            self._close_recording_tabs(record_id)

    def open_settings_tab(self):
        self.setup_actions.open_settings_tab()

    def import_audio_file(self, config):
        self.setup_actions.import_audio_file(config)

    def open_collections_list(self):
        self.sidebar_content.open_collections_list()

    def open_notebooks_list(self):
        self.sidebar_content.open_notebooks_list()

    def open_notebook(self, notebook_id, name):
        self.sidebar_content.open_notebook(notebook_id, name)

    def open_notebook_chat(self, notebook_id, notebook_name):
        self.sidebar_content.open_notebook_chat(notebook_id, notebook_name)

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
            self.chat_floating.remove_floating_host(host)

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
        self.chat_floating.reposition_floating_chat_bar()
        logging.warning("MainWindow.closeEvent completed.")
