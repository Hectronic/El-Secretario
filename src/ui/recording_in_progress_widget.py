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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QProgressBar, QComboBox, QSpacerItem, QSizePolicy,
                             QLineEdit, QFormLayout, QGroupBox, QCheckBox, QCompleter)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from src.audio import Recorder
from src.database import DBManager

class RecordingInProgressWidget(QWidget):
    finished = pyqtSignal(str, dict)  # Emits file path and config when finished
    cancelled = pyqtSignal()   # Emits when cancelled

    def __init__(self, recorder=None, config=None, parent=None):
        super().__init__(parent)
        self.recorder = recorder or Recorder()
        self.recorder.amplitude_changed.connect(self.update_vu_meter)
        self.config = config or {}
        self.recording_started = False
        self.db = DBManager()  # For tags autocomplete
        
        # Set device from config if provided
        if self.config.get("device_index") is not None:
            self.recorder.set_device(self.config["device_index"])
        
        self.duration_seconds = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        
        self.init_ui()
        
        # Auto-start recording
        self.start_recording()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Status Label
        self.status_label = QLabel("Recording in Progress...")
        self.status_label.setStyleSheet("font-size: 24px; color: #f44336; font-weight: bold;")
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Timer
        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #eeeeee;")
        layout.addWidget(self.timer_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # VU Meter
        self.vu_meter = QProgressBar()
        self.vu_meter.setRange(0, 100)
        self.vu_meter.setTextVisible(False)
        self.vu_meter.setFixedSize(400, 20)
        self.vu_meter.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                background-color: #333;
            }
            QProgressBar::chunk {
                background-color: #f44336;
                width: 10px;
            }
        """)
        layout.addWidget(self.vu_meter, alignment=Qt.AlignmentFlag.AlignCenter)

        # Recording Options Group
        options_group = QGroupBox("Recording Options")
        options_group.setMinimumWidth(450)
        options_group.setStyleSheet("""
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
        options_layout = QFormLayout()
        options_layout.setSpacing(10)

        # Title field
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter recording title...")
        options_layout.addRow("Title:", self.title_input)

        # Tags field with autocomplete
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Work, Meeting, ...")
        all_tags = self.db.get_all_tags()
        self.tags_completer = QCompleter(all_tags)
        self.tags_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.tags_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.tags_input.setCompleter(self.tags_completer)
        options_layout.addRow("Tags:", self.tags_input)

        # Model selector
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        initial_model = self.config.get("model", "base")
        self.model_combo.setCurrentText(initial_model)
        options_layout.addRow("Model:", self.model_combo)

        # Diarization checkbox
        self.diarization_check = QCheckBox("Enable speaker diarization")
        self.diarization_check.setToolTip("Enable speaker diarization (Requires HF Token)")
        self.diarization_check.setChecked(self.config.get("diarization", False))
        options_layout.addRow("", self.diarization_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group, alignment=Qt.AlignmentFlag.AlignCenter)

        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(20)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setFixedSize(120, 50)
        self.pause_btn.setStyleSheet("font-size: 16px;")
        self.pause_btn.clicked.connect(self.toggle_pause)
        controls_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Finish")
        self.stop_btn.setFixedSize(120, 50)
        self.stop_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px; font-weight: bold;")
        self.stop_btn.clicked.connect(self.finish_recording)
        controls_layout.addWidget(self.stop_btn)

        layout.addLayout(controls_layout)
        
        # Cancel Button
        self.cancel_btn = QPushButton("Cancel Recording")
        self.cancel_btn.setStyleSheet("color: #888; text-decoration: underline; border: none; background: none;")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_recording)
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def start_recording(self):
        try:
            if not self.recorder.is_recording:
                self.recorder.start()
            self.recording_started = True
            self.timer.start(1000)
        except Exception as e:
            self.recording_started = False
            self.status_label.setText(f"Error: {e}")
            self.status_label.setStyleSheet("font-size: 18px; color: #f44336; font-weight: bold;")
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

    def toggle_pause(self):
        if not self.recording_started:
            return
        if self.recorder.is_paused:
            self.recorder.resume()
            self.pause_btn.setText("Pause")
            self.status_label.setText("Recording in Progress...")
            self.timer.start(1000)
        else:
            self.recorder.pause()
            self.pause_btn.setText("Resume")
            self.status_label.setText("Recording Paused")
            self.timer.stop()

    def finish_recording(self):
        self.timer.stop()
        if not self.recording_started:
            # If recording never started, just cancel
            self.cancelled.emit()
            return
        file_path = self.recorder.stop()
        if file_path:
            # Build final config with user inputs
            final_config = {
                **self.config,
                "title": self.title_input.text().strip(),
                "tags": self.tags_input.text().strip(),
                "model": self.model_combo.currentText(),
                "diarization": self.diarization_check.isChecked()
            }
            self.finished.emit(file_path, final_config)
        else:
            self.cancelled.emit()

    def cancel_recording(self):
        self.timer.stop()
        if self.recording_started:
            try:
                self.recorder.stop()
            except Exception:
                pass  # Ignore errors when cancelling
        self.cancelled.emit()

    def update_timer(self):
        self.duration_seconds += 1
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        self.timer_label.setText(f"{minutes:02}:{seconds:02}")

    def update_vu_meter(self, amplitude):
        value = int(amplitude * 1000)
        if value > 100: value = 100
        self.vu_meter.setValue(value)

