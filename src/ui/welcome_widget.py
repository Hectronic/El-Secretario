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

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy, QLineEdit, QListWidget, QListWidgetItem, QComboBox, QCheckBox, QGroupBox, QFormLayout, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap
from src.ui.styles import LIST_WIDGET_STYLE
from src.ui.styles import LIST_WIDGET_STYLE
from src.audio import Recorder
import sounddevice as sd
import numpy as np
import os

class WelcomeWidget(QWidget):
    # Modified signal to include recording configuration
    new_recording_requested = pyqtSignal(dict)  # Emits config dict
    search_requested = pyqtSignal() # Kept for compatibility if needed, but likely unused now
    search_triggered = pyqtSignal(str)
    result_clicked = pyqtSignal(int)
    new_chat_requested = pyqtSignal()
    batch_process_requested = pyqtSignal()  # Kept for compatibility
    import_audio_requested = pyqtSignal(dict)  # Also include config for import
    notebooks_requested = pyqtSignal()
    maintenance_requested = pyqtSignal()  # Kept for compatibility
    tools_requested = pyqtSignal()  # Unified tools signal
    settings_requested = pyqtSignal() # New settings signal

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.favorites_page = 0
        self.test_stream = None
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.update_test_vu)
        self.current_amplitude = 0.0
        self.init_ui()
        self.load_favorites()
        self.load_today()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(os.getcwd(), "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale if too big, e.g., max height 150
            pixmap = pixmap.scaledToHeight(150, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Title
        title = QLabel("El Secretario")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #2196F3;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("What would you like to do today?")
        subtitle.setStyleSheet("font-size: 18px; color: gray;")
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search your notes...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 16px;
                border: 2px solid #ddd;
                border-radius: 10px;
                min-width: 400px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        self.search_input.returnPressed.connect(self.on_search_triggered)
        layout.addWidget(self.search_input, alignment=Qt.AlignmentFlag.AlignCenter)

        # Recording Configuration and Record Button Row
        rec_config_row = QHBoxLayout()
        rec_config_row.setSpacing(30)
        rec_config_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Recording Configuration Group
        config_group = QGroupBox("Recording Configuration")
        config_group.setMinimumWidth(500)
        config_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        config_layout = QFormLayout()
        config_layout.setSpacing(10)

        # Mic Selector with Test Button
        mic_row = QHBoxLayout()
        self.mic_combo = QComboBox()
        self.mic_combo.setMinimumWidth(250)
        self.populate_mics()
        mic_row.addWidget(self.mic_combo)
        
        self.test_mic_btn = QPushButton("🎤 Test")
        self.test_mic_btn.setFixedWidth(80)
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
        self.test_mic_btn.clicked.connect(self.toggle_mic_test)
        mic_row.addWidget(self.test_mic_btn)
        
        config_layout.addRow("Audio Source:", mic_row)
        
        # VU Meter for testing (hidden initially)
        self.test_vu_meter = QProgressBar()
        self.test_vu_meter.setRange(0, 100)
        self.test_vu_meter.setTextVisible(False)
        self.test_vu_meter.setFixedHeight(20)
        self.test_vu_meter.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                background-color: #333;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        self.test_vu_meter.hide()
        config_layout.addRow("", self.test_vu_meter)
        
        self.test_status_label = QLabel("")
        self.test_status_label.setStyleSheet("color: #888; font-size: 12px;")
        self.test_status_label.hide()
        config_layout.addRow("", self.test_status_label)

        # Model Selector
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText("base")
        config_layout.addRow("Model:", self.model_combo)

        # Language Selector
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Auto", "Spanish", "English"])
        config_layout.addRow("Language:", self.lang_combo)

        # Diarization Checkbox
        self.diarization_check = QCheckBox("Enable speaker diarization")
        self.diarization_check.setToolTip("Enable speaker diarization (Requires HF Token)")
        config_layout.addRow("", self.diarization_check)

        config_group.setLayout(config_layout)

        # Large Round Record Button
        self.rec_btn = self.create_round_button("REC", "#f44336", self.on_new_recording, size=140)
        rec_config_row.addWidget(self.rec_btn)
        
        rec_config_row.addWidget(config_group)

        layout.addLayout(rec_config_row)

        # Secondary Buttons Row (more compact)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.chat_btn = self.create_big_button("Start Chat", "#4CAF50", self.new_chat_requested.emit, width=160, height=60)
        self.import_btn = self.create_big_button("Import Audio", "#9C27B0", self.on_import_audio, width=160, height=60)
        self.tools_btn = self.create_big_button("⚙️ Tools", "#607D8B", self.tools_requested.emit, width=160, height=60)
        self.settings_btn = self.create_big_button("🔧 Settings", "#009688", self.settings_requested.emit, width=160, height=60)

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
        self.fav_list.setFixedHeight(180)
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
        self.today_list.setFixedHeight(180)
        self.today_list.setStyleSheet(LIST_WIDGET_STYLE)
        self.today_list.itemClicked.connect(self.on_today_clicked)
        today_container.addWidget(self.today_list)
        
        # Stats for today
        self.today_stats = QLabel("")
        self.today_stats.setStyleSheet("font-size: 12px; color: #888;")
        today_container.addWidget(self.today_stats)
        
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

    def populate_mics(self):
        """Populate the microphone combo box with available devices."""
        devices = Recorder.get_input_devices()
        self.mic_combo.clear()
        # Add default option first
        self.mic_combo.addItem("Default (Auto)", None)
        for idx, name in devices:
            self.mic_combo.addItem(name, idx)

    def toggle_mic_test(self):
        """Toggle microphone testing on/off."""
        if self.test_stream is not None:
            self.stop_mic_test()
        else:
            self.start_mic_test()

    def start_mic_test(self):
        """Start testing the selected microphone."""
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
            "diarization": self.diarization_check.isChecked()
        }

    def on_new_recording(self):
        """Emit new recording signal with configuration."""
        config = self.get_recording_config()
        self.new_recording_requested.emit(config)

    def on_import_audio(self):
        """Emit import audio signal with configuration."""
        config = self.get_recording_config()
        self.import_audio_requested.emit(config)

    def create_big_button(self, text, color, callback, width=200, height=150):
        btn = QPushButton(text)
        btn.setFixedSize(width, height)
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

    def create_round_button(self, text, color, callback, size=120):
        btn = QPushButton(text)
        btn.setFixedSize(size, size)
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
        
        total_duration = 0.0
        for rec in records:
            title = rec['title'] if rec['title'] else rec['filename']
            duration = rec['duration'] or 0.0
            total_duration += duration
            
            # Format duration nicely
            mins = int(duration // 60)
            secs = int(duration % 60)
            duration_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            
            item = QListWidgetItem(f"{title} ({duration_str})")
            item.setData(Qt.ItemDataRole.UserRole, rec['id'])
            self.today_list.addItem(item)
        
        # Update stats
        count = len(records)
        total_mins = int(total_duration // 60)
        if count == 0:
            self.today_stats.setText("No recordings today")
        else:
            self.today_stats.setText(f"{count} recording(s) • Total: {total_mins} min")

    def on_today_clicked(self, item):
        record_id = int(item.data(Qt.ItemDataRole.UserRole))
        self.result_clicked.emit(record_id)



