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

import platform

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy, QLineEdit, QListWidget, QListWidgetItem, QComboBox, QCheckBox, QGroupBox, QFormLayout, QProgressBar, QTextBrowser, QScrollArea, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings, QTime, QPointF
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
from src.ui.styles import LIST_WIDGET_STYLE
import numpy as np
import os

Recorder = None

class AnalogClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(92, 92)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)

    def paintEvent(self, _event):
        side = min(self.width(), self.height())
        now = QTime.currentTime()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 100.0, side / 100.0)

        painter.setPen(QPen(QColor("#CFD8DC"), 3))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(-46, -46, 92, 92)

        for i in range(12):
            painter.save()
            painter.rotate(i * 30)
            painter.setPen(QPen(QColor("#78909C"), 2 if i % 3 else 3))
            painter.drawLine(0, -38, 0, -44)
            painter.restore()

        hour_angle = 30 * ((now.hour() % 12) + now.minute() / 60.0)
        minute_angle = 6 * (now.minute() + now.second() / 60.0)
        second_angle = 6 * now.second()

        painter.save()
        painter.rotate(hour_angle)
        painter.setPen(QPen(QColor("#37474F"), 5, cap=Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0, 5), QPointF(0, -21))
        painter.restore()

        painter.save()
        painter.rotate(minute_angle)
        painter.setPen(QPen(QColor("#455A64"), 3, cap=Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0, 7), QPointF(0, -30))
        painter.restore()

        painter.save()
        painter.rotate(second_angle)
        painter.setPen(QPen(QColor("#E53935"), 1.5, cap=Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0, 9), QPointF(0, -33))
        painter.restore()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#E53935"))
        painter.drawEllipse(-3, -3, 6, 6)


class WelcomeWidget(QWidget):
    # Modified signal to include recording configuration
    new_recording_requested = pyqtSignal(dict)  # Emits config dict
    search_requested = pyqtSignal() # Kept for compatibility if needed, but likely unused now
    search_triggered = pyqtSignal(str)
    result_clicked = pyqtSignal(int)
    new_chat_requested = pyqtSignal()
    ask_chat_with_context_requested = pyqtSignal()
    new_note_requested = pyqtSignal()
    batch_process_requested = pyqtSignal()  # Kept for compatibility
    import_audio_requested = pyqtSignal(dict)  # Also include config for import
    notebooks_requested = pyqtSignal()
    maintenance_requested = pyqtSignal()  # Kept for compatibility
    tools_requested = pyqtSignal()  # Unified tools signal
    settings_requested = pyqtSignal() # New settings signal
    generate_daily_summary_requested = pyqtSignal()
    status_message_requested = pyqtSignal(str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._is_windows = platform.system() == "Windows"
        self._compact_mode_active = False
        self.favorites_page = 0
        self.test_stream = None
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.update_test_vu)
        self.settings = QSettings("Hectronic", "Secretario")
        self.current_amplitude = 0.0
        self.init_ui()
        self.load_favorites()
        self.load_today()
        self._load_saved_config()
        self._connect_config_signals()

    def _load_saved_config(self):
        saved_mic = self.settings.value("rec_config/mic", None)
        prefer_index = self.settings.value("audio_prefer_device_index", False, type=bool)
        if saved_mic is None:
            # Try global default from settings.
            if prefer_index:
                saved_mic_index = self.settings.value("default_mic_index", None)
                try:
                    index = self.mic_combo.findData(int(saved_mic_index)) if saved_mic_index is not None else -1
                except (TypeError, ValueError):
                    index = -1
                if index >= 0:
                    self.mic_combo.setCurrentIndex(index)
            if self.mic_combo.currentIndex() <= 0:
                saved_mic_name = self.settings.value("default_mic_name", "")
                if saved_mic_name:
                    index = self.mic_combo.findText(saved_mic_name)
                    if index >= 0:
                        self.mic_combo.setCurrentIndex(index)
        elif saved_mic:
            index = self.mic_combo.findData(saved_mic)
            if index >= 0:
                self.mic_combo.setCurrentIndex(index)
        
        saved_model = self.settings.value("rec_config/model", None)
        if saved_model is None:
            saved_model = self.settings.value("whisper_model", "large-v3")
        self.model_combo.setCurrentText(saved_model)
        
        saved_lang = self.settings.value("rec_config/language", "Auto")
        self.lang_combo.setCurrentText(saved_lang)
        
        saved_diar = self.settings.value("rec_config/diarization", False, type=bool)
        self.diarization_check.setChecked(saved_diar)
        
        saved_sys_audio = self.settings.value("rec_config/capture_system_audio", None)
        if saved_sys_audio is None:
            # Try global default from settings
            saved_sys_audio = self.settings.value("capture_system_audio", False, type=bool)
        else:
            saved_sys_audio = self.settings.value("rec_config/capture_system_audio", False, type=bool)
            
        self.sys_audio_check.setChecked(saved_sys_audio)

        saved_auto_summary = self.settings.value("rec_config/auto_summarize_after_transcription", False, type=bool)
        self.auto_summary_check.setChecked(saved_auto_summary)
        
    def _connect_config_signals(self):
        self.mic_combo.currentIndexChanged.connect(self._save_config)
        self.model_combo.currentIndexChanged.connect(self._save_config)
        self.lang_combo.currentIndexChanged.connect(self._save_config)
        self.diarization_check.toggled.connect(self._save_config)
        self.sys_audio_check.toggled.connect(self._save_config)
        self.auto_summary_check.toggled.connect(self._save_config)

    def _save_config(self):
        self.settings.setValue("rec_config/mic", self.mic_combo.currentData())
        self.settings.setValue("rec_config/model", self.model_combo.currentText())
        self.settings.setValue("rec_config/language", self.lang_combo.currentText())
        self.settings.setValue("rec_config/diarization", self.diarization_check.isChecked())
        self.settings.setValue("rec_config/capture_system_audio", self.sys_audio_check.isChecked())
        self.settings.setValue("rec_config/auto_summarize_after_transcription", self.auto_summary_check.isChecked())
        self.status_message_requested.emit("Recording configuration saved.")

    def _update_digital_clock(self):
        self.digital_clock_label.setText(QTime.currentTime().toString("HH:mm:ss"))
        self._sync_header_balance()

    def _sync_header_balance(self):
        if not hasattr(self, "header_left_spacer"):
            return
        clock_width = max(self.analog_clock.width(), self.digital_clock_label.sizeHint().width())
        self.header_left_spacer.setFixedWidth(clock_width)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root_layout.addWidget(self.scroll_area)

        content = QWidget()
        self.scroll_area.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(14)
        self.main_content_layout = layout

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

        self.header_left_spacer = QWidget()
        self.header_left_spacer.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(10)
        brand_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        logo_label = QLabel()
        self.brand_logo = logo_label
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
        self.brand_title = title
        brand_row.addWidget(title, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        brand_search_column.addLayout(brand_row)

        clock_column = QVBoxLayout()
        clock_column.setContentsMargins(0, 0, 0, 0)
        clock_column.setSpacing(2)
        clock_column.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.analog_clock = AnalogClockWidget()
        clock_column.addWidget(self.analog_clock, 0, Qt.AlignmentFlag.AlignHCenter)
        self.digital_clock_label = QLabel()
        self.digital_clock_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1E3A5F;")
        clock_column.addWidget(self.digital_clock_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search your notes...")
        self.search_input.setStyleSheet("""
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
        self.search_input.setMinimumHeight(38)
        self.search_input.returnPressed.connect(self.on_search_triggered)
        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(0)
        search_row.addStretch()
        search_row.addWidget(self.search_input, 0, Qt.AlignmentFlag.AlignHCenter)
        search_row.addStretch()
        brand_search_column.addLayout(search_row, 1)

        search_actions_row = QHBoxLayout()
        search_actions_row.setContentsMargins(0, 0, 0, 0)
        search_actions_row.setSpacing(12)
        search_actions_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.search_btn = self.create_big_button("Buscar", "#1565C0", self.on_search_triggered, width=150, height=44)
        self.ask_btn = self.create_big_button("Preguntar", "#2E7D32", self.ask_chat_with_context_requested.emit, width=150, height=44)
        search_actions_row.addWidget(self.search_btn)
        search_actions_row.addWidget(self.ask_btn)
        brand_search_column.addLayout(search_actions_row)

        header_row.addWidget(self.header_left_spacer, 0, Qt.AlignmentFlag.AlignTop)
        header_row.addLayout(brand_search_column, 1)
        header_row.addLayout(clock_column, 0)
        header_layout.addLayout(header_row)
        layout.addWidget(header_container)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_digital_clock)
        self.clock_timer.start(1000)
        self._update_digital_clock()
        self._sync_header_balance()

        # === Recording Configuration Section ===
        rec_config_row = QHBoxLayout()
        rec_config_row.setSpacing(0)
        rec_config_row.setContentsMargins(40, 10, 40, 10)
        rec_config_row.addStretch()

        # REC Button Container (bordered, rounded left side)
        self.rec_container = QWidget()
        self.rec_container.setObjectName("rec_container")
        self.rec_container.setProperty("class", "welcome-rec-container")
        rec_container_layout = QVBoxLayout(self.rec_container)
        rec_container_layout.setContentsMargins(0, 0, 0, 0)
        rec_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rec_btn = self.create_round_button("REC", "#f44336", self.on_new_recording, size=85, class_name="rec-btn")
        rec_container_layout.addWidget(self.rec_btn, 0, Qt.AlignmentFlag.AlignCenter)
        rec_config_row.addWidget(self.rec_container)

        # Config area (Modern card style with title inside)
        self.config_group = QGroupBox()
        self.config_group.setObjectName("config_group")
        self.config_group.setProperty("class", "welcome-config-group")
        self.config_group.setFixedWidth(450)
        self.config_group.setFixedHeight(160)
        
        inner_config_layout = QVBoxLayout(self.config_group)
        inner_config_layout.setContentsMargins(5, 10, 5, 10)
        inner_config_layout.setSpacing(0)

        config_layout = QFormLayout()
        config_layout.setContentsMargins(15, 5, 15, 5)
        config_layout.setSpacing(8)

        # Mic Selector with Test Button
        mic_row = QHBoxLayout()
        self.mic_combo = QComboBox()
        self.mic_combo.setMinimumWidth(180)
        self.populate_mics()
        mic_row.addWidget(self.mic_combo)

        self.rescan_mics_btn = QPushButton("🔄 Re-scan")
        self.rescan_mics_btn.setFixedWidth(95)
        self.rescan_mics_btn.setToolTip("Re-scan USB and system recording devices")
        self.rescan_mics_btn.setStyleSheet("""
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
        self.rescan_mics_btn.clicked.connect(self.on_rescan_mics_clicked)
        mic_row.addWidget(self.rescan_mics_btn)
        
        self.test_mic_btn = QPushButton("🎤 Test")
        self.test_mic_btn.setFixedWidth(80)
        self.test_mic_btn.setStyleSheet("""
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
        self.test_mic_btn.clicked.connect(self.toggle_mic_test)
        mic_row.addWidget(self.test_mic_btn)
        
        mic_label = QLabel("🎤 Microphone:")
        mic_label.setProperty("class", "welcome-config-label")
        config_layout.addRow(mic_label, mic_row)
        
        # VU Meter for testing (hidden initially)
        self.test_vu_meter = QProgressBar()
        self.test_vu_meter.setRange(0, 100)
        self.test_vu_meter.setTextVisible(False)
        self.test_vu_meter.setFixedHeight(15)
        self.test_vu_meter.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        self.test_vu_meter.hide()
        config_layout.addRow("", self.test_vu_meter)
        
        self.test_status_label = QLabel("")
        self.test_status_label.setStyleSheet("color: #90A4AE; font-size: 11px;")
        self.test_status_label.hide()
        config_layout.addRow("", self.test_status_label)

        # Row 1: Model & Language
        ml_row = QHBoxLayout()
        ml_row.setSpacing(10)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText("base")
        self.model_combo.setMinimumWidth(80)
        
        model_label = QLabel("🧠 Model:")
        model_label.setProperty("class", "welcome-config-label")
        ml_row.addWidget(model_label)
        ml_row.addWidget(self.model_combo, 1)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Auto", "Spanish", "English"])
        self.lang_combo.setMinimumWidth(80)
        
        lang_label = QLabel("🌐 Lang:")
        lang_label.setProperty("class", "welcome-config-label")
        ml_row.addWidget(lang_label)
        ml_row.addWidget(self.lang_combo, 1)
        
        config_layout.addRow(ml_row)

        # Row 2: Checkboxes
        check_row = QHBoxLayout()
        check_row.setSpacing(15)
        
        self.diarization_check = QCheckBox("👥 Diarization")
        self.diarization_check.setToolTip("Enable speaker diarization (Requires HF Token)")
        self.diarization_check.setProperty("class", "welcome-config-check")
        check_row.addWidget(self.diarization_check)
        
        self.sys_audio_check = QCheckBox("🖥️ PC Internal Audio")
        self.sys_audio_check.setToolTip("Capture audio from the computer (speakers/internal)")
        self.sys_audio_check.setStyleSheet("""
            QCheckBox {
                color: #FFB74D;
                font-weight: bold;
                background-color: transparent;
            }
            QCheckBox:hover {
                color: #FFCC80;
            }
        """)
        check_row.addWidget(self.sys_audio_check)

        self.auto_summary_check = QCheckBox("📝 Auto summary")
        self.auto_summary_check.setToolTip("Generate summary automatically when transcription completes")
        self.auto_summary_check.setProperty("class", "welcome-config-check")
        check_row.addWidget(self.auto_summary_check)
        
        config_layout.addRow(check_row)

        inner_config_layout.addLayout(config_layout)
        rec_config_row.addWidget(self.config_group)

        # NOTE Button (right side, rounded right corners)
        self.new_note_top_btn = self.create_squircle_button("NOTE", "#2196F3", self.new_note_requested.emit, width=110, height=160, class_name="new-note-btn")
        rec_config_row.addWidget(self.new_note_top_btn)
        rec_config_row.addStretch()

        layout.addLayout(rec_config_row)

        # Secondary Buttons Row (more compact)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.chat_btn = self.create_big_button("Start Chat", "#4CAF50", self.new_chat_requested.emit, width=160, height=60, class_name="big-btn-chat")
        self.import_btn = self.create_big_button("Import Audio", "#9C27B0", self.on_import_audio, width=160, height=60, class_name="big-btn-import")
        self.tools_btn = self.create_big_button("⚙️ Tools", "#607D8B", self.tools_requested.emit, width=160, height=60, class_name="big-btn-tools")
        self.settings_btn = self.create_big_button("🔧 Settings", "#009688", self.settings_requested.emit, width=160, height=60, class_name="big-btn-settings")

        btn_layout.addWidget(self.chat_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.tools_btn)
        btn_layout.addWidget(self.settings_btn)

        layout.addLayout(btn_layout)


        
        # Two-column layout for Favorites and Today's Summary
        lists_layout = QHBoxLayout()
        lists_layout.setSpacing(20)
        
        # Favorites Section (left)
        fav_container = QVBoxLayout()
        self.fav_label = QLabel("⭐ Favorites")
        self.fav_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px;")
        fav_container.addWidget(self.fav_label)
        
        self.fav_list = QListWidget()
        self.fav_list.setMinimumHeight(140)
        self.fav_list.setMaximumHeight(220)
        self.fav_list.setStyleSheet(LIST_WIDGET_STYLE)
        self.fav_list.itemClicked.connect(self.on_fav_clicked)
        fav_container.addWidget(self.fav_list)
        
        # Pagination Controls for Favorites
        pag_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.setFixedWidth(70)
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.setFixedWidth(70)
        self.next_btn.clicked.connect(self.next_page)
        
        pag_layout.addWidget(self.prev_btn)
        pag_layout.addWidget(self.next_btn)
        pag_layout.addStretch()
        fav_container.addLayout(pag_layout)
        
        lists_layout.addLayout(fav_container)
        
        # Today's Summary Section (right)
        today_container = QVBoxLayout()
        self.today_label = QLabel("📅 Today's Recordings")
        self.today_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px;")
        today_container.addWidget(self.today_label)
        
        self.today_list = QListWidget()
        self.today_list.setMinimumHeight(140)
        self.today_list.setMaximumHeight(220)
        self.today_list.setStyleSheet(LIST_WIDGET_STYLE)
        self.today_list.itemClicked.connect(self.on_today_clicked)
        today_container.addWidget(self.today_list)
        
        # We don't add addStretch here so it uses the same visual spacing as Favorites
        
        self.generate_daily_summary_btn = QPushButton("Generate Daily Summary")
        self.generate_daily_summary_btn.setProperty("class", "calendar-nav-btn")
        self.generate_daily_summary_btn.clicked.connect(self.generate_daily_summary_requested.emit)
        today_container.addWidget(self.generate_daily_summary_btn)
        
        lists_layout.addLayout(today_container)
        
        layout.addLayout(lists_layout)
        
        # Results List (for search)
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
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
        self.results_list.hide() # Hidden initially
        self.results_list.itemClicked.connect(self.on_result_clicked)
        layout.addWidget(self.results_list)
        
        # Add some space at the bottom
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self._apply_layout_density()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_layout_density()

    def _apply_layout_density(self, viewport_height=None):
        """
        Adapt welcome layout to low-height viewports.
        On Windows we switch earlier because DPI scaling frequently reduces usable height.
        """
        if viewport_height is None:
            if hasattr(self, "scroll_area") and self.scroll_area.viewport():
                viewport_height = self.scroll_area.viewport().height()
            else:
                viewport_height = self.height()

        compact_threshold = 980 if self._is_windows else 860
        compact_mode = viewport_height > 0 and viewport_height < compact_threshold

        if compact_mode != self._compact_mode_active:
            self._compact_mode_active = compact_mode

        viewport_width = self.scroll_area.viewport().width() if hasattr(self, "scroll_area") and self.scroll_area.viewport() else self.width()

        if compact_mode:
            self.main_content_layout.setContentsMargins(18, 8, 18, 8)
            self.main_content_layout.setSpacing(10)
            self.brand_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
            self.analog_clock.setFixedSize(78, 78)
            self.digital_clock_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #1E3A5F;")
            self.rec_container.setFixedSize(96, 142)
            self._set_rec_button_size(72)
            self.new_note_top_btn.setFixedSize(96, 142)
            self.config_group.setFixedHeight(142)
            self.fav_list.setMinimumHeight(120)
            self.fav_list.setMaximumHeight(170)
            self.today_list.setMinimumHeight(120)
            self.today_list.setMaximumHeight(170)
            search_min_width = 360
        else:
            self.main_content_layout.setContentsMargins(24, 12, 24, 12)
            self.main_content_layout.setSpacing(14)
            self.brand_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
            self.analog_clock.setFixedSize(92, 92)
            self.digital_clock_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1E3A5F;")
            self.rec_container.setFixedSize(110, 160)
            self._set_rec_button_size(85)
            self.new_note_top_btn.setFixedSize(110, 160)
            self.config_group.setFixedHeight(160)
            self.fav_list.setMinimumHeight(140)
            self.fav_list.setMaximumHeight(220)
            self.today_list.setMinimumHeight(140)
            self.today_list.setMaximumHeight(220)
            search_min_width = 440

        max_search_width = max(search_min_width, min(920, viewport_width - 220))
        self.search_input.setMinimumWidth(search_min_width)
        self.search_input.setMaximumWidth(max_search_width)
        self._sync_header_balance()

        target_config_width = 410 if compact_mode else 450
        available_width = max(320, viewport_width - 360)
        self.config_group.setFixedWidth(min(target_config_width, available_width))

        btn_width = 145 if compact_mode else 160
        btn_height = 52 if compact_mode else 60
        self.search_btn.setFixedSize(135 if compact_mode else 150, 40 if compact_mode else 44)
        self.ask_btn.setFixedSize(135 if compact_mode else 150, 40 if compact_mode else 44)

        for btn in (self.chat_btn, self.import_btn, self.tools_btn, self.settings_btn):
            btn.setFixedSize(btn_width, btn_height)

    def _set_rec_button_size(self, size):
        """Keep REC visually circular regardless of active theme and compact mode."""
        self.rec_btn.setFixedSize(size, size)
        self.rec_btn.setStyleSheet(f"border-radius: {size // 2}px;")

    def populate_mics(self, keep_current=False):
        """Populate the microphone combo box with available devices."""
        previous_data = self.mic_combo.currentData() if keep_current else None
        previous_text = self.mic_combo.currentText() if keep_current else ""
        if os.environ.get("EL_SECRETARIO_SKIP_AUDIO_ENUM", "").strip().lower() in {"1", "true", "yes"}:
            self.mic_combo.clear()
            self.mic_combo.addItem("Default (Auto)", None)
            return
        global Recorder
        if Recorder is None:
            from src.audio import Recorder as _Recorder
            Recorder = _Recorder
        devices = Recorder.get_input_devices()
        self.mic_combo.clear()
        # Add default option first
        self.mic_combo.addItem("Default (Auto)", None)
        for idx, name in devices:
            self.mic_combo.addItem(name, idx)
        if keep_current:
            if previous_data is not None:
                idx_by_data = self.mic_combo.findData(previous_data)
                if idx_by_data >= 0:
                    self.mic_combo.setCurrentIndex(idx_by_data)
                    return
            if previous_text:
                idx_by_text = self.mic_combo.findText(previous_text)
                if idx_by_text >= 0:
                    self.mic_combo.setCurrentIndex(idx_by_text)

    def on_rescan_mics_clicked(self):
        self.populate_mics(keep_current=True)
        detected = max(0, self.mic_combo.count() - 1)
        if detected > 0:
            self.status_message_requested.emit(f"Audio re-scan complete: {detected} input device(s) detected.")
        else:
            self.status_message_requested.emit("Audio re-scan complete: no input devices detected, using default.")

    def toggle_mic_test(self):
        """Toggle microphone testing on/off."""
        if self.test_stream is not None:
            self.stop_mic_test()
        else:
            self.start_mic_test()

    def start_mic_test(self):
        """Start testing the selected microphone."""
        import sounddevice as sd
        device_index = self.mic_combo.currentData()
        
        # Try different sample rates
        sample_rates = [16000, 44100, 48000, 22050]
        
        for rate in sample_rates:
            try:
                self.test_stream = sd.InputStream(
                    samplerate=rate,
                    channels=1,
                    callback=self.test_audio_callback,
                    device=device_index
                )
                self.test_stream.start()
                self.test_vu_meter.show()
                self.test_status_label.setText(f"Testing at {rate} Hz - Speak into the mic...")
                self.test_status_label.show()
                self.test_mic_btn.setText("⏹ Stop")
                self.test_mic_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        border-radius: 5px;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: #d32f2f;
                    }
                """)
                self.test_timer.start(50)  # Update VU meter every 50ms
                return
            except Exception as e:
                continue
        
        # All rates failed
        self.test_status_label.setText("Error: Could not open audio device")
        self.test_status_label.setStyleSheet("color: #f44336; font-size: 12px;")
        self.test_status_label.show()

    def stop_mic_test(self):
        """Stop testing the microphone."""
        self.test_timer.stop()
        if self.test_stream is not None:
            try:
                self.test_stream.stop()
                self.test_stream.close()
            except:
                pass
            self.test_stream = None
        
        self.test_vu_meter.setValue(0)
        self.test_vu_meter.hide()
        self.test_status_label.hide()
        self.test_mic_btn.setText("🎤 Test")
        self.test_mic_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

    def test_audio_callback(self, indata, frames, time, status):
        """Callback for test audio stream."""
        rms = np.sqrt(np.mean(indata**2))
        self.current_amplitude = rms

    def update_test_vu(self):
        """Update the test VU meter."""
        value = int(self.current_amplitude * 1000)
        if value > 100:
            value = 100
        self.test_vu_meter.setValue(value)
        
        # Change color based on level
        if value > 70:
            self.test_vu_meter.setStyleSheet("""
                QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #333; }
                QProgressBar::chunk { background-color: #f44336; }
            """)
        elif value > 30:
            self.test_vu_meter.setStyleSheet("""
                QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #333; }
                QProgressBar::chunk { background-color: #4CAF50; }
            """)
        else:
            self.test_vu_meter.setStyleSheet("""
                QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #333; }
                QProgressBar::chunk { background-color: #2196F3; }
            """)

    def get_recording_config(self):
        """Get the current recording configuration."""
        # Stop mic test if running
        if self.test_stream is not None:
            self.stop_mic_test()
            
        lang_map = {"Auto": None, "Spanish": "es", "English": "en"}
        return {
            "device_index": self.mic_combo.currentData(),
            "model": self.model_combo.currentText(),
            "language": lang_map.get(self.lang_combo.currentText()),
            "diarization": self.diarization_check.isChecked(),
            "capture_system_audio": self.sys_audio_check.isChecked(),
            "auto_summarize_after_transcription": self.auto_summary_check.isChecked(),
        }

    def on_new_recording(self):
        """Emit new recording signal with configuration."""
        if self.settings.value("audio_rescan_before_capture", True, type=bool):
            self.populate_mics(keep_current=True)
        config = self.get_recording_config()
        self.new_recording_requested.emit(config)

    def on_import_audio(self):
        """Emit import audio signal with configuration."""
        if self.settings.value("audio_rescan_before_capture", True, type=bool):
            self.populate_mics(keep_current=True)
        config = self.get_recording_config()
        self.import_audio_requested.emit(config)

    def create_big_button(self, text, color, callback, width=200, height=150, class_name=None):
        btn = QPushButton(text)
        if class_name:
            btn.setProperty("class", class_name)
        btn.setFixedSize(width, height)
        
        # Only apply hardcoded style if NO class is provided
        if not class_name:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background-color: {color}cc;
                }}
            """)
        btn.clicked.connect(callback)
        return btn

    def create_round_button(self, text, color, callback, size=120, class_name=None):
        btn = QPushButton(text)
        if class_name:
            btn.setProperty("class", class_name)
        btn.setFixedSize(size, size)
        
        if not class_name:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    border-radius: {size // 2}px;
                    border: 5px solid #fff;
                }}
                QPushButton:hover {{
                    background-color: {color}cc;
                    border-color: #eee;
                }}
                QPushButton:pressed {{
                    background-color: {color}aa;
                    border-color: #ccc;
                }}
            """)
        btn.clicked.connect(callback)
        return btn

    def create_squircle_button(self, text, color, callback, width=100, height=90, class_name=None):
        from PyQt6.QtGui import QColor
        btn = QPushButton(text)
        if class_name:
            btn.setProperty("class", class_name)
        btn.setFixedSize(width, height)
        border_radius = int(height * 0.25)
        
        if not class_name:
            bg = QColor(color)
            hover_bg = bg.lighter(115).name()
            pressed_bg = bg.darker(110).name()

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    border-top-right-radius: {border_radius}px;
                    border-bottom-right-radius: {border_radius}px;
                    border-top-left-radius: 0px;
                    border-bottom-left-radius: 0px;
                    border: 2px solid #555;
                    border-left: none;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                    border: 2px solid #777;
                    border-left: none;
                }}
                QPushButton:pressed {{
                    background-color: {pressed_bg};
                    border: 2px solid #999;
                    border-left: none;
                }}
            """)
        btn.clicked.connect(callback)
        return btn

    def on_search_triggered(self):
        text = self.search_input.text().strip()
        if text:
            self.search_triggered.emit(text)

    def display_results(self, results):
        self.results_list.clear()
        if not results:
            self.results_list.hide()
            return
        
        self.results_list.show()
        for res in results:
            title = res['metadata'].get('title', 'Untitled')
            item_text = f"{title} (Score: {1 - res['distance']:.2f})\n{res['text'][:100]}..."
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, res['id'])
            self.results_list.addItem(item)

    def on_result_clicked(self, item):
        record_id = int(item.data(Qt.ItemDataRole.UserRole))
        self.result_clicked.emit(record_id)
        
    def load_favorites(self):
        self.fav_list.clear()
        favorites = self.db.fetch_favorites(limit=5, offset=self.favorites_page * 5)
        
        if not favorites and self.favorites_page > 0:
            self.favorites_page -= 1
            self.load_favorites()
            return

        for fav in favorites:
            title = fav['title'] if fav['title'] else fav['created_at']
            item = QListWidgetItem(f"{title} ({fav['duration']:.1f}s)")
            item.setData(Qt.ItemDataRole.UserRole, fav['id'])
            self.fav_list.addItem(item)
            
        self.prev_btn.setEnabled(self.favorites_page > 0)
        # Check if there are more
        next_batch = self.db.fetch_favorites(limit=1, offset=(self.favorites_page + 1) * 5)
        self.next_btn.setEnabled(bool(next_batch))

    def prev_page(self):
        if self.favorites_page > 0:
            self.favorites_page -= 1
            self.load_favorites()

    def next_page(self):
        self.favorites_page += 1
        self.load_favorites()
        
    def on_fav_clicked(self, item):
        record_id = int(item.data(Qt.ItemDataRole.UserRole))
        self.result_clicked.emit(record_id)

    def load_today(self):
        """Load today's recordings."""
        from datetime import date
        self.today_list.clear()
        
        today_str = date.today().isoformat()
        records = self.db.fetch_by_date_range(today_str, today_str)
        
        for rec in records:
            if rec.get('type') == 'note':
                title = rec['title'] if rec['title'] else "Untitled Note"
                item_text = f"📝 {title}"
            else:
                title = rec['title'] if rec['title'] else rec['created_at']
                dur = rec.get('duration', 0)
                item_text = f"🎤 {title} ({dur:.1f}s)"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, rec['id'])
            self.today_list.addItem(item)

    def on_today_clicked(self, item):
        record_id = int(item.data(Qt.ItemDataRole.UserRole))
        self.result_clicked.emit(record_id)

    def save_settings(self):
        """Save current settings to QSettings."""
        self.settings.setValue("whisper_model", self.model_combo.currentText())
        self.settings.setValue("whisper_language", self.lang_combo.currentText())
        self.settings.sync() # Ensure settings are written to disk

# End of assumed class content
