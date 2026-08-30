"""Construcción de la jerarquía visual principal de la aplicación."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSplitter,
    QStyle,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.main_window.chat_context_sidebar import install_chat_context_sidebar_section
from src.ui.styles import NEW_CHAT_BUTTON_STYLE



def build_main_window_layout(window):
        central_widget = QWidget()
        window.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        window.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(window.splitter)

        # --- Left Panel: History & Search ---
        left_widget = QWidget()
        left_widget.setMinimumWidth(300) # Slightly wider for the custom items
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # Calendar Widget
        window.calendar = QCalendarWidget()
        window.calendar.setGridVisible(True)
        window.calendar.selectionChanged.connect(window.on_calendar_date_changed)
        # Set a fixed height or max height so it doesn't take too much space
        window.calendar.setMaximumHeight(300)
        left_layout.addWidget(window.calendar)

        # Week Details Button
        window.open_calendar_btn = QPushButton("Week Details")
        window.open_calendar_btn.clicked.connect(window.open_calendar_tab)
        window.open_calendar_btn.setProperty("class", "calendar-primary-btn")
        window.open_calendar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.open_calendar_btn.setMinimumHeight(36)
        left_layout.addWidget(window.open_calendar_btn)

        # Calendar Navigation
        nav_layout = QHBoxLayout()
        window.prev_week_btn = QPushButton("<< Prev Week")
        window.prev_week_btn.clicked.connect(window.prev_week_sidebar)
        window.prev_week_btn.setProperty("class", "calendar-nav-btn")
        window.prev_week_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.prev_week_btn.setMinimumHeight(34)

        window.reset_date_btn = QPushButton("all")
        window.reset_date_btn.clicked.connect(window.reset_date_filter)
        window.reset_date_btn.setProperty("class", "calendar-nav-btn")
        window.reset_date_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.reset_date_btn.setMinimumHeight(34)

        window.next_week_btn = QPushButton("Next Week >>")
        window.next_week_btn.clicked.connect(window.next_week_sidebar)
        window.next_week_btn.setProperty("class", "calendar-nav-btn")
        window.next_week_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.next_week_btn.setMinimumHeight(34)
        nav_layout.addWidget(window.prev_week_btn)
        nav_layout.addWidget(window.reset_date_btn)
        nav_layout.addWidget(window.next_week_btn)
        left_layout.addLayout(nav_layout)

        # Initialize date filter state
        window.current_date_filter = None # Single date (string) or None for week/all
        window.current_week_monday = None # QDate of Monday if filtering by week

        # Default view: no date filter (show all recordings at startup)
        QTimer.singleShot(100, window.update_calendar_visuals)

        # Search Box
        search_layout = QHBoxLayout()
        window.search_input = QLineEdit()
        window.search_input.setPlaceholderText("Search recordings...")
        window.search_input.textChanged.connect(window.filter_history_list)
        search_layout.addWidget(window.search_input)
        left_layout.addLayout(search_layout)

        # Filter Row (Tags)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        window.tag_filter_combo = QComboBox()
        window.tag_filter_combo.addItem("All")
        window.tag_filter_combo.currentTextChanged.connect(window.on_tag_filter_changed)
        filter_layout.addWidget(window.tag_filter_combo)

        window.fav_filter_cb = QCheckBox("★")
        window.fav_filter_cb.setToolTip("Show Favorites Only")
        window.fav_filter_cb.stateChanged.connect(window.load_history)
        filter_layout.addWidget(window.fav_filter_cb)

        # Refresh Button
        window.refresh_btn = QPushButton()
        window.refresh_btn.setIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        window.refresh_btn.setToolTip("Refresh List")
        window.refresh_btn.setFixedSize(24, 24)
        window.refresh_btn.clicked.connect(window.refresh_sidebar)
        filter_layout.addWidget(window.refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

        left_layout.addLayout(filter_layout)

        # History List
        window.history_list = QListWidget()
        # Disable horizontal scrolling - long titles will be clipped
        window.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # window.history_list.setStyleSheet(LIST_WIDGET_STYLE) # Use Global Theme
        window.history_list.itemClicked.connect(window.on_history_item_clicked)
        window.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        window.history_list.customContextMenuRequested.connect(window.show_history_item_context_menu)
        left_layout.addWidget(window.history_list)

        window.splitter.addWidget(left_widget)

        # --- Middle Panel: Tabbed Interface ---
        window.central_tabs = QTabWidget()
        window.central_tabs.setTabsClosable(True)
        window.central_tabs.tabCloseRequested.connect(window.close_tab)
        window.central_tabs.currentChanged.connect(window._on_central_tab_changed)
        window.central_tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        window.central_tabs.customContextMenuRequested.connect(window.show_tab_context_menu)
        window.splitter.addWidget(window.central_tabs)
        # --- Right Panel: Accordion (Tasks, Chat History, Notebooks, Tags) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        window._right_sidebar_layout = right_layout
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
            header_btn.clicked.connect(lambda _checked=False, key=section_key: window._on_right_section_header_clicked(key))
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
            window._right_sidebar_sections[section_key] = {
                "title": title,
                "header": header_btn,
                "header_shell": header_shell,
                "content": content_widget,
                "container": container,
            }
            return container

        # 1. Tasks Section
        window.tasks_sidebar_list = QListWidget()
        window.tasks_sidebar_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        window.tasks_sidebar_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        window.tasks_sidebar_list.customContextMenuRequested.connect(window.show_tasks_sidebar_context_menu)

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

        window.create_task_btn = QToolButton()
        window.create_task_btn.setText("+")
        window.create_task_btn.setToolTip("Create a new task")
        window.create_task_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.create_task_btn.setAutoRaise(True)
        window.create_task_btn.setFixedSize(28, 28)
        window.create_task_btn.setStyleSheet(task_action_style)
        window.create_task_btn.clicked.connect(lambda: window.open_tasks_tab(create_new=True))

        window.open_tasks_btn = QToolButton()
        window.open_tasks_btn.setText("⤢")
        window.open_tasks_btn.setToolTip("Open the full Tasks tab")
        window.open_tasks_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.open_tasks_btn.setAutoRaise(True)
        window.open_tasks_btn.setFixedSize(28, 28)
        window.open_tasks_btn.setStyleSheet(task_action_style)
        window.open_tasks_btn.clicked.connect(lambda: window.open_tasks_tab(create_new=False))

        window.tasks_header_actions = QWidget()
        tasks_header_layout = QHBoxLayout(window.tasks_header_actions)
        tasks_header_layout.setContentsMargins(0, 0, 0, 0)
        tasks_header_layout.setSpacing(2)
        tasks_header_layout.addWidget(window.create_task_btn)
        tasks_header_layout.addWidget(window.open_tasks_btn)

        tasks_section = create_section("tasks", "✅ Tasks", window.tasks_sidebar_list, header_actions=window.tasks_header_actions)
        right_layout.addWidget(tasks_section)
        window._right_sidebar_sections["tasks"]["index"] = right_layout.indexOf(tasks_section)

        # 2. Chat History Section
        window.sessions_list = QListWidget()
        window.sessions_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        window.sessions_list.itemClicked.connect(window.on_chat_session_clicked)
        window.sessions_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        window.sessions_list.customContextMenuRequested.connect(window.show_chat_sidebar_context_menu)

        window.new_chat_btn = QToolButton()
        window.new_chat_btn.setText("+")
        window.new_chat_btn.setToolTip("Start a new chat")
        window.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.new_chat_btn.setAutoRaise(True)
        window.new_chat_btn.setFixedSize(28, 28)
        window.new_chat_btn.setStyleSheet(task_action_style)
        window.new_chat_btn.clicked.connect(lambda: window.open_chat_tab(None))

        window.open_chat_history_btn = QToolButton()
        window.open_chat_history_btn.setText("⤢")
        window.open_chat_history_btn.setToolTip("Open the full Chat History tab")
        window.open_chat_history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.open_chat_history_btn.setAutoRaise(True)
        window.open_chat_history_btn.setFixedSize(28, 28)
        window.open_chat_history_btn.setStyleSheet(task_action_style)
        window.open_chat_history_btn.clicked.connect(window.open_chat_history_tab)

        window.chats_header_actions = QWidget()
        chats_header_layout = QHBoxLayout(window.chats_header_actions)
        chats_header_layout.setContentsMargins(0, 0, 0, 0)
        chats_header_layout.setSpacing(2)
        chats_header_layout.addWidget(window.new_chat_btn)
        chats_header_layout.addWidget(window.open_chat_history_btn)

        chat_section = create_section("chats", "💬 Chat History", window.sessions_list, header_actions=window.chats_header_actions)
        right_layout.addWidget(chat_section)
        window._right_sidebar_sections["chats"]["index"] = right_layout.indexOf(chat_section)

        # 3. Libretas (Notebooks) Section
        window.notebooks_list = QListWidget()
        window.notebooks_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        window.notebooks_list.itemClicked.connect(window.on_notebook_clicked)
        window.notebooks_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        window.notebooks_list.customContextMenuRequested.connect(window.show_notebooks_sidebar_context_menu)

        window.create_notebook_btn = QToolButton()
        window.create_notebook_btn.setText("+")
        window.create_notebook_btn.setToolTip("Create a new notebook")
        window.create_notebook_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.create_notebook_btn.setAutoRaise(True)
        window.create_notebook_btn.setFixedSize(28, 28)
        window.create_notebook_btn.setStyleSheet(task_action_style)
        window.create_notebook_btn.clicked.connect(window.create_notebook)

        window.open_notebooks_btn = QToolButton()
        window.open_notebooks_btn.setText("⤢")
        window.open_notebooks_btn.setToolTip("Open the full Notebooks tab")
        window.open_notebooks_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.open_notebooks_btn.setAutoRaise(True)
        window.open_notebooks_btn.setFixedSize(28, 28)
        window.open_notebooks_btn.setStyleSheet(task_action_style)
        window.open_notebooks_btn.clicked.connect(window.open_notebooks_list)

        window.notebooks_header_actions = QWidget()
        notebooks_header_layout = QHBoxLayout(window.notebooks_header_actions)
        notebooks_header_layout.setContentsMargins(0, 0, 0, 0)
        notebooks_header_layout.setSpacing(2)
        notebooks_header_layout.addWidget(window.create_notebook_btn)
        notebooks_header_layout.addWidget(window.open_notebooks_btn)

        nb_section = create_section("notebooks", "📓 Notebooks", window.notebooks_list, header_actions=window.notebooks_header_actions)
        right_layout.addWidget(nb_section)
        window._right_sidebar_sections["notebooks"]["index"] = right_layout.indexOf(nb_section)

        # 4. Tags Section
        window.collections_list = QListWidget()
        window.collections_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        window.collections_list.itemClicked.connect(window.on_collection_clicked)
        window.collections_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        window.collections_list.customContextMenuRequested.connect(window.show_tags_sidebar_context_menu)

        window.new_tag_chat_btn = QToolButton()
        window.new_tag_chat_btn.setText("+")
        window.new_tag_chat_btn.setToolTip("Start a chat for the selected tag")
        window.new_tag_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.new_tag_chat_btn.setAutoRaise(True)
        window.new_tag_chat_btn.setFixedSize(28, 28)
        window.new_tag_chat_btn.setStyleSheet(task_action_style)
        window.new_tag_chat_btn.clicked.connect(window.open_selected_tag_chat)

        window.open_collections_btn = QToolButton()
        window.open_collections_btn.setText("⤢")
        window.open_collections_btn.setToolTip("Open the full Collections tab")
        window.open_collections_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.open_collections_btn.setAutoRaise(True)
        window.open_collections_btn.setFixedSize(28, 28)
        window.open_collections_btn.setStyleSheet(task_action_style)
        window.open_collections_btn.clicked.connect(window.open_collections_list)

        window.tags_header_actions = QWidget()
        tags_header_layout = QHBoxLayout(window.tags_header_actions)
        tags_header_layout.setContentsMargins(0, 0, 0, 0)
        tags_header_layout.setSpacing(2)
        tags_header_layout.addWidget(window.new_tag_chat_btn)
        tags_header_layout.addWidget(window.open_collections_btn)

        tags_section = create_section("tags", "🏷️ Tags", window.collections_list, header_actions=window.tags_header_actions)
        right_layout.addWidget(tags_section)
        window._right_sidebar_sections["tags"]["index"] = right_layout.indexOf(tags_section)

        # 5. Active Chat Context Section
        install_chat_context_sidebar_section(
            window,
            right_panel=right_panel,
            right_layout=right_layout,
            create_section=create_section,
        )

        right_layout.addStretch(1)
        window._right_sidebar_bottom_spacer_index = right_layout.count() - 1

        # Independent bottom section: Settings (outside accordion logic)
        right_settings_section = QWidget()
        right_settings_layout = QVBoxLayout(right_settings_section)
        right_settings_layout.setContentsMargins(0, 6, 0, 0)
        right_settings_layout.setSpacing(6)

        window.right_settings_label = QLabel("⚙️ Settings")
        window.right_settings_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #2196F3;")
        right_settings_layout.addWidget(window.right_settings_label)

        window.right_settings_btn = QPushButton("Open Settings")
        window.right_settings_btn.setProperty("class", "calendar-nav-btn")
        window.right_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        window.right_settings_btn.setMinimumHeight(34)
        window.right_settings_btn.clicked.connect(window.open_settings_tab)
        right_settings_layout.addWidget(window.right_settings_btn)

        right_layout.addWidget(right_settings_section)
        window._set_active_right_section("tasks")

        window.splitter.addWidget(right_panel)

        window.floating_chat_bar = QFrame(central_widget)
        window.floating_chat_bar.setObjectName("floatingChatBar")
        window.floating_chat_bar.setStyleSheet("""
            QFrame#floatingChatBar {
                background-color: transparent;
                border: none;
            }
        """)
        window.floating_chat_bar.setVisible(False)
        window.floating_chat_layout = QHBoxLayout(window.floating_chat_bar)
        window.floating_chat_layout.setContentsMargins(0, 0, 0, 0)
        window.floating_chat_layout.setSpacing(12)
        window.floating_chat_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        window.floating_chat_bar.raise_()

        # Set initial sizes for the three panels
        # Left: 300 (min), Middle: 700 (rest), Right: 300 (min)
        window.splitter.setSizes([300, 700, 300])

        # Enforce stretch factors to ensure right panel takes up space
        window.splitter.setStretchFactor(0, 0) # Left panel doesn't stretch
        window.splitter.setStretchFactor(1, 1) # Middle panel stretches
        window.splitter.setStretchFactor(2, 0) # Right panel doesn't stretch

        window.splitter.setCollapsible(0, False)
        window.splitter.setCollapsible(1, False)
        window.splitter.setCollapsible(2, False)

        window.runtime_startup.initialize_rag_from_settings()


