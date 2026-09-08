"""Visual composition and responsive sizing for the welcome screen."""

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from src.transcription_options import (
    DEFAULT_TRANSCRIPTION_MODEL,
    get_transcription_model_options,
)
from src.ui.styles import LIST_WIDGET_STYLE


def build_welcome_layout(widget, analog_clock_cls):
        root_layout = QVBoxLayout(widget)
        root_layout.setContentsMargins(0, 0, 0, 0)

        widget.scroll_area = QScrollArea()
        widget.scroll_area.setWidgetResizable(True)
        widget.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        widget.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root_layout.addWidget(widget.scroll_area)

        content = QWidget()
        widget.scroll_area.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(14)
        widget.main_content_layout = layout

        # Header block: brand and search aligned with the clock on the same top row
        header_container = QWidget()
        header_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(0)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(18)

        brand_search_column = QVBoxLayout()
        brand_search_column.setContentsMargins(0, 0, 0, 0)
        brand_search_column.setSpacing(10)

        widget.header_left_spacer = QWidget()
        widget.header_left_spacer.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(10)
        brand_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        logo_label = QLabel()
        widget.brand_logo = logo_label
        # Robust logo path for PyInstaller or local dev
        import sys
        def get_resource_path(relative_path):
            base_path = getattr(sys, '_MEIPASS', os.getcwd())
            return os.path.join(base_path, relative_path)
        
        logo_path = get_resource_path("logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Compact logo for top header
            pixmap = pixmap.scaledToHeight(58, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            brand_row.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        title = QLabel("El Secretario")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        widget.brand_title = title
        brand_row.addWidget(title, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        brand_search_column.addLayout(brand_row)

        clock_column = QVBoxLayout()
        clock_column.setContentsMargins(0, 0, 0, 0)
        clock_column.setSpacing(2)
        clock_column.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        widget.analog_clock = analog_clock_cls()
        clock_column.addWidget(widget.analog_clock, 0, Qt.AlignmentFlag.AlignHCenter)
        widget.digital_clock_label = QLabel()
        widget.digital_clock_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1E3A5F;")
        clock_column.addWidget(widget.digital_clock_label, 0, Qt.AlignmentFlag.AlignHCenter)

        widget.search_input = QLineEdit()
        widget.search_input.setPlaceholderText("Search your notes...")
        widget.search_input.setStyleSheet("""
            QLineEdit {
                background: white;
                padding: 8px 12px;
                font-size: 15px;
                border: 2px solid #C7D7E4;
                border-radius: 10px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        widget.search_input.setMinimumHeight(38)
        widget.search_input.returnPressed.connect(widget.on_search_triggered)
        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(0)
        search_row.addStretch()
        search_row.addWidget(widget.search_input, 0, Qt.AlignmentFlag.AlignHCenter)
        search_row.addStretch()
        brand_search_column.addLayout(search_row, 1)

        search_actions_row = QHBoxLayout()
        search_actions_row.setContentsMargins(0, 0, 0, 0)
        search_actions_row.setSpacing(12)
        search_actions_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        widget.search_btn = widget.create_big_button("Buscar", "#1565C0", widget.on_search_triggered, width=150, height=44)
        widget.ask_btn = widget.create_big_button("Preguntar", "#2E7D32", widget.ask_chat_with_context_requested.emit, width=150, height=44)
        search_actions_row.addWidget(widget.search_btn)
        search_actions_row.addWidget(widget.ask_btn)
        brand_search_column.addLayout(search_actions_row)

        header_row.addWidget(widget.header_left_spacer, 0, Qt.AlignmentFlag.AlignTop)
        header_row.addLayout(brand_search_column, 1)
        header_row.addLayout(clock_column, 0)
        header_layout.addLayout(header_row)
        layout.addWidget(header_container)

        widget.clock_timer = QTimer(widget)
        widget.clock_timer.timeout.connect(widget._update_digital_clock)
        widget.clock_timer.start(1000)
        widget._update_digital_clock()
        widget._sync_header_balance()

        # === Recording Configuration Section ===
        rec_config_row = QHBoxLayout()
        rec_config_row.setSpacing(0)
        rec_config_row.setContentsMargins(40, 10, 40, 10)
        rec_config_row.addStretch()

        # REC Button Container (bordered, rounded left side)
        widget.rec_container = QWidget()
        widget.rec_container.setObjectName("rec_container")
        widget.rec_container.setProperty("class", "welcome-rec-container")
        rec_container_layout = QVBoxLayout(widget.rec_container)
        rec_container_layout.setContentsMargins(0, 0, 0, 0)
        rec_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.rec_btn = widget.create_round_button("REC", "#f44336", widget.on_new_recording, size=85, class_name="rec-btn")
        rec_container_layout.addWidget(widget.rec_btn, 0, Qt.AlignmentFlag.AlignCenter)
        rec_config_row.addWidget(widget.rec_container)

        # Config area (Modern card style with title inside)
        widget.config_group = QGroupBox()
        widget.config_group.setObjectName("config_group")
        widget.config_group.setProperty("class", "welcome-config-group")
        widget.config_group.setFixedWidth(450)
        widget.config_group.setFixedHeight(160)
        
        inner_config_layout = QVBoxLayout(widget.config_group)
        inner_config_layout.setContentsMargins(5, 10, 5, 10)
        inner_config_layout.setSpacing(0)

        config_layout = QFormLayout()
        config_layout.setContentsMargins(15, 5, 15, 5)
        config_layout.setSpacing(8)

        # Mic Selector with Test Button
        mic_row = QHBoxLayout()
        widget.mic_combo = QComboBox()
        widget.mic_combo.setMinimumWidth(180)
        widget.populate_mics()
        mic_row.addWidget(widget.mic_combo)

        widget.rescan_mics_btn = QPushButton("🔄 Re-scan")
        widget.rescan_mics_btn.setFixedWidth(95)
        widget.rescan_mics_btn.setToolTip("Re-scan USB and system recording devices")
        widget.rescan_mics_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        widget.rescan_mics_btn.clicked.connect(widget.on_rescan_mics_clicked)
        mic_row.addWidget(widget.rescan_mics_btn)
        
        widget.test_mic_btn = QPushButton("🎤 Test")
        widget.test_mic_btn.setFixedWidth(80)
        widget.test_mic_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        widget.test_mic_btn.clicked.connect(widget.toggle_mic_test)
        mic_row.addWidget(widget.test_mic_btn)
        
        mic_label = QLabel("🎤 Microphone:")
        mic_label.setProperty("class", "welcome-config-label")
        config_layout.addRow(mic_label, mic_row)
        
        # VU Meter for testing (hidden initially)
        widget.test_vu_meter = QProgressBar()
        widget.test_vu_meter.setRange(0, 100)
        widget.test_vu_meter.setTextVisible(False)
        widget.test_vu_meter.setFixedHeight(15)
        widget.test_vu_meter.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        widget.test_vu_meter.hide()
        config_layout.addRow("", widget.test_vu_meter)
        
        widget.test_status_label = QLabel("")
        widget.test_status_label.setStyleSheet("color: #90A4AE; font-size: 11px;")
        widget.test_status_label.hide()
        config_layout.addRow("", widget.test_status_label)

        # Row 1: Model & Language
        ml_row = QHBoxLayout()
        ml_row.setSpacing(10)
        
        widget.model_combo = QComboBox()
        widget.model_combo.addItems(get_transcription_model_options())
        widget.model_combo.setCurrentText(DEFAULT_TRANSCRIPTION_MODEL)
        widget.model_combo.setMinimumWidth(80)
        
        model_label = QLabel("🧠 Model:")
        model_label.setProperty("class", "welcome-config-label")
        ml_row.addWidget(model_label)
        ml_row.addWidget(widget.model_combo, 1)

        widget.lang_combo = QComboBox()
        widget.lang_combo.addItems(["Auto", "Spanish", "English"])
        widget.lang_combo.setMinimumWidth(80)
        
        lang_label = QLabel("🌐 Lang:")
        lang_label.setProperty("class", "welcome-config-label")
        ml_row.addWidget(lang_label)
        ml_row.addWidget(widget.lang_combo, 1)
        
        config_layout.addRow(ml_row)

        # Row 2: Checkboxes
        check_row = QHBoxLayout()
        check_row.setSpacing(15)
        
        widget.diarization_check = QCheckBox("👥 Diarization")
        widget.diarization_check.setToolTip("Enable speaker diarization (Requires HF Token)")
        widget.diarization_check.setProperty("class", "welcome-config-check")
        check_row.addWidget(widget.diarization_check)
        
        widget.sys_audio_check = QCheckBox("🖥️ PC Internal Audio")
        widget.sys_audio_check.setToolTip("Capture audio from the computer (speakers/internal)")
        widget.sys_audio_check.setStyleSheet("""
            QCheckBox {
                color: #FFB74D;
                font-weight: bold;
                background-color: transparent;
            }
            QCheckBox:hover {
                color: #FFCC80;
            }
        """)
        check_row.addWidget(widget.sys_audio_check)

        widget.auto_summary_check = QCheckBox("📝 Auto summary")
        widget.auto_summary_check.setToolTip("Generate summary automatically when transcription completes")
        widget.auto_summary_check.setProperty("class", "welcome-config-check")
        check_row.addWidget(widget.auto_summary_check)
        
        config_layout.addRow(check_row)

        inner_config_layout.addLayout(config_layout)
        rec_config_row.addWidget(widget.config_group)

        # NOTE Button (right side, rounded right corners)
        widget.new_note_top_btn = widget.create_squircle_button("NOTE", "#2196F3", widget.new_note_requested.emit, width=110, height=160, class_name="new-note-btn")
        rec_config_row.addWidget(widget.new_note_top_btn)
        rec_config_row.addStretch()

        layout.addLayout(rec_config_row)

        # Secondary Buttons Row (more compact)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        widget.chat_btn = widget.create_big_button("Start Chat", "#4CAF50", widget.new_chat_requested.emit, width=160, height=60, class_name="big-btn-chat")
        widget.import_btn = widget.create_big_button("Import Audio", "#9C27B0", widget.on_import_audio, width=160, height=60, class_name="big-btn-import")
        widget.tools_btn = widget.create_big_button("⚙️ Tools", "#607D8B", widget.tools_requested.emit, width=160, height=60, class_name="big-btn-tools")
        widget.settings_btn = widget.create_big_button("🔧 Settings", "#009688", widget.settings_requested.emit, width=160, height=60, class_name="big-btn-settings")

        btn_layout.addWidget(widget.chat_btn)
        btn_layout.addWidget(widget.import_btn)
        btn_layout.addWidget(widget.tools_btn)
        btn_layout.addWidget(widget.settings_btn)

        layout.addLayout(btn_layout)


        
        # Two-column layout for Favorites and Today's Summary
        lists_layout = QHBoxLayout()
        lists_layout.setSpacing(20)
        
        # Favorites Section (left)
        fav_container = QVBoxLayout()
        widget.fav_label = QLabel("⭐ Favorites")
        widget.fav_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px;")
        fav_container.addWidget(widget.fav_label)
        
        widget.fav_list = QListWidget()
        widget.fav_list.setMinimumHeight(140)
        widget.fav_list.setMaximumHeight(220)
        widget.fav_list.setStyleSheet(LIST_WIDGET_STYLE)
        widget.fav_list.itemClicked.connect(widget.on_fav_clicked)
        fav_container.addWidget(widget.fav_list)
        
        # Pagination Controls for Favorites
        pag_layout = QHBoxLayout()
        widget.prev_btn = QPushButton("◀ Prev")
        widget.prev_btn.setFixedWidth(70)
        widget.prev_btn.clicked.connect(widget.prev_page)
        widget.next_btn = QPushButton("Next ▶")
        widget.next_btn.setFixedWidth(70)
        widget.next_btn.clicked.connect(widget.next_page)
        
        pag_layout.addWidget(widget.prev_btn)
        pag_layout.addWidget(widget.next_btn)
        pag_layout.addStretch()
        fav_container.addLayout(pag_layout)
        
        lists_layout.addLayout(fav_container)
        
        # Today's Summary Section (right)
        today_container = QVBoxLayout()
        widget.today_label = QLabel("📅 Today's Recordings")
        widget.today_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px;")
        today_container.addWidget(widget.today_label)
        
        widget.today_list = QListWidget()
        widget.today_list.setMinimumHeight(140)
        widget.today_list.setMaximumHeight(220)
        widget.today_list.setStyleSheet(LIST_WIDGET_STYLE)
        widget.today_list.itemClicked.connect(widget.on_today_clicked)
        today_container.addWidget(widget.today_list)
        
        # We don't add addStretch here so it uses the same visual spacing as Favorites
        
        widget.generate_daily_summary_btn = QPushButton("Generate Daily Summary")
        widget.generate_daily_summary_btn.setProperty("class", "calendar-nav-btn")
        widget.generate_daily_summary_btn.clicked.connect(widget.generate_daily_summary_requested.emit)
        today_container.addWidget(widget.generate_daily_summary_btn)
        
        lists_layout.addLayout(today_container)
        
        layout.addLayout(lists_layout)
        
        # Results List (for search)
        widget.results_list = QListWidget()
        widget.results_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #444;
                border-radius: 5px;
                background-color: #2b2b2b;
                color: #eeeeee;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #3a3a3a;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
        """)
        widget.results_list.hide() # Hidden initially
        widget.results_list.itemClicked.connect(widget.on_result_clicked)
        layout.addWidget(widget.results_list)
        
        # Add some space at the bottom
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        widget._apply_layout_density()



def apply_layout_density(widget, viewport_height=None):
        """
        Adapt welcome layout to low-height viewports.
        On Windows we switch earlier because DPI scaling frequently reduces usable height.
        """
        if viewport_height is None:
            if hasattr(widget, "scroll_area") and widget.scroll_area.viewport():
                viewport_height = widget.scroll_area.viewport().height()
            else:
                viewport_height = widget.height()

        compact_threshold = 980 if widget._is_windows else 860
        compact_mode = viewport_height > 0 and viewport_height < compact_threshold

        if compact_mode != widget._compact_mode_active:
            widget._compact_mode_active = compact_mode

        viewport_width = widget.scroll_area.viewport().width() if hasattr(widget, "scroll_area") and widget.scroll_area.viewport() else widget.width()

        if compact_mode:
            widget.main_content_layout.setContentsMargins(18, 8, 18, 8)
            widget.main_content_layout.setSpacing(10)
            widget.brand_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
            widget.analog_clock.setFixedSize(78, 78)
            widget.digital_clock_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #1E3A5F;")
            widget.rec_container.setFixedSize(96, 142)
            widget._set_rec_button_size(72)
            widget.new_note_top_btn.setFixedSize(96, 142)
            widget.config_group.setFixedHeight(142)
            widget.fav_list.setMinimumHeight(120)
            widget.fav_list.setMaximumHeight(170)
            widget.today_list.setMinimumHeight(120)
            widget.today_list.setMaximumHeight(170)
            search_min_width = 360
        else:
            widget.main_content_layout.setContentsMargins(24, 12, 24, 12)
            widget.main_content_layout.setSpacing(14)
            widget.brand_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
            widget.analog_clock.setFixedSize(92, 92)
            widget.digital_clock_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1E3A5F;")
            widget.rec_container.setFixedSize(110, 160)
            widget._set_rec_button_size(85)
            widget.new_note_top_btn.setFixedSize(110, 160)
            widget.config_group.setFixedHeight(160)
            widget.fav_list.setMinimumHeight(140)
            widget.fav_list.setMaximumHeight(220)
            widget.today_list.setMinimumHeight(140)
            widget.today_list.setMaximumHeight(220)
            search_min_width = 440

        max_search_width = max(search_min_width, min(920, viewport_width - 220))
        widget.search_input.setMinimumWidth(search_min_width)
        widget.search_input.setMaximumWidth(max_search_width)
        widget._sync_header_balance()

        target_config_width = 410 if compact_mode else 450
        available_width = max(320, viewport_width - 360)
        widget.config_group.setFixedWidth(min(target_config_width, available_width))

        btn_width = 145 if compact_mode else 160
        btn_height = 52 if compact_mode else 60
        widget.search_btn.setFixedSize(135 if compact_mode else 150, 40 if compact_mode else 44)
        widget.ask_btn.setFixedSize(135 if compact_mode else 150, 40 if compact_mode else 44)

        for btn in (widget.chat_btn, widget.import_btn, widget.tools_btn, widget.settings_btn):
            btn.setFixedSize(btn_width, btn_height)



def set_rec_button_size(widget, size):
        """Keep REC visually circular regardless of active theme and compact mode."""
        widget.rec_btn.setFixedSize(size, size)
        widget.rec_btn.setStyleSheet(f"border-radius: {size // 2}px;")

