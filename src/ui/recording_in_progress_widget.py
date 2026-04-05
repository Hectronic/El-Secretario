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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QProgressBar, QComboBox, QSpacerItem, QSizePolicy,
                             QLineEdit, QFormLayout, QGroupBox, QCheckBox, QTextEdit,
                             QListWidget, QListWidgetItem, QSplitter, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSettings
import logging
from src.database import DBManager
from src.ui.components import TagsLineEdit
from src.transcription_options import (
    DEFAULT_TRANSCRIPTION_MODEL,
    get_transcription_model_options,
    normalize_transcription_model,
)

Recorder = None

class RecordingInProgressWidget(QWidget):
    finished = pyqtSignal(str, dict)  # Emits file path and config when finished
    cancelled = pyqtSignal()   # Emits when cancelled

    def __init__(self, recorder=None, config=None, parent=None):
        super().__init__(parent)
        self._is_windows = platform.system() == "Windows"
        self._compact_mode_active = False
        if recorder is not None:
            self.recorder = recorder
        else:
            global Recorder
            if Recorder is None:
                from src.audio import Recorder as _Recorder
                Recorder = _Recorder
            self.recorder = Recorder()
        self.recorder.amplitude_changed.connect(self.update_vu_meter)
        self._amplitude_connected = True
        self.config = config or {}
        self.recording_started = False
        self._is_finishing = False
        self.db = DBManager()  # For tags autocomplete
        self.settings = QSettings("Hectronic", "Secretario")
        
        # Set device from config if provided
        if self.config.get("device_index") is not None:
            self.recorder.set_device(self.config["device_index"])
            
        if self.config.get("capture_system_audio"):
            self.recorder.set_capture_machine_audio(True)
        
        self.duration_seconds = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        
        self.init_ui()
        
        # Auto-start recording
        self.start_recording()

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
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_content_layout = layout

        # Status Label
        self.status_label = QLabel("Recording in Progress...")
        self.status_label.setStyleSheet("font-size: 24px; color: #f44336; font-weight: bold;")
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Timer
        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #eeeeee;")
        layout.addWidget(self.timer_label, alignment=Qt.AlignmentFlag.AlignHCenter)

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
        layout.addWidget(self.vu_meter, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        controls_layout.setContentsMargins(0, 4, 0, 4)
        controls_layout.addStretch(1)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setProperty("class", "calendar-nav-btn")
        self.pause_btn.setFixedSize(124, 50)
        self.pause_btn.clicked.connect(self.toggle_pause)
        controls_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Finish")
        self.stop_btn.setProperty("class", "calendar-primary-btn")
        self.stop_btn.setFixedSize(124, 50)
        self.stop_btn.clicked.connect(self.finish_recording)
        controls_layout.addWidget(self.stop_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "record-del-btn")
        self.cancel_btn.setFixedSize(124, 50)
        self.cancel_btn.clicked.connect(self.cancel_recording)
        controls_layout.addWidget(self.cancel_btn)
        controls_layout.addStretch(1)
        layout.addLayout(controls_layout)

        # Recording Options Group
        self.options_group = QGroupBox("Recording Options")
        self.options_group.setStyleSheet("""
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
        self.tags_input = TagsLineEdit()
        all_tags = self.db.get_all_tags()
        self.tags_input.set_tags(all_tags)
        options_layout.addRow("Tags:", self.tags_input)

        # Model selector
        self.model_combo = QComboBox()
        self.model_combo.addItems(get_transcription_model_options())
        initial_model = normalize_transcription_model(
            self.config.get("model", DEFAULT_TRANSCRIPTION_MODEL)
        )
        self.model_combo.setCurrentText(initial_model)
        options_layout.addRow("Model:", self.model_combo)

        # Diarization checkbox
        self.diarization_check = QCheckBox("Enable speaker diarization")
        self.diarization_check.setToolTip("Enable speaker diarization (Requires HF Token)")
        self.diarization_check.setChecked(self.config.get("diarization", False))
        options_layout.addRow("", self.diarization_check)

        # Auto-summary after transcription
        default_auto_summary = self.settings.value(
            "rec_config/auto_summarize_after_transcription",
            False,
            type=bool,
        )
        self.auto_summary_check = QCheckBox("Summarize automatically after transcription")
        self.auto_summary_check.setToolTip("Queues an AI summary as soon as transcription is done")
        self.auto_summary_check.setChecked(
            self.config.get("auto_summarize_after_transcription", default_auto_summary)
        )
        options_layout.addRow("", self.auto_summary_check)
        self.model_combo.currentTextChanged.connect(self._save_last_run_config)
        self.diarization_check.toggled.connect(self._save_last_run_config)
        self.auto_summary_check.toggled.connect(self._save_last_run_config)

        self.options_group.setLayout(options_layout)
        layout.addWidget(self.options_group)

        self.workspace_split = QSplitter(Qt.Orientation.Horizontal)

        self.notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout(self.notes_group)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Write important context while recording...")
        self.notes_input.setMinimumHeight(220)
        self.notes_input.setStyleSheet("font-size: 14px; line-height: 1.4;")
        notes_layout.addWidget(self.notes_input)
        self.workspace_split.addWidget(self.notes_group)

        self.tasks_group = QGroupBox("Quick Tasks")
        tasks_layout = QVBoxLayout(self.tasks_group)
        quick_add = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Add actionable task and press Add...")
        self.task_input.returnPressed.connect(self.add_quick_task)
        self.add_task_btn = QPushButton("Add")
        self.add_task_btn.clicked.connect(self.add_quick_task)
        quick_add.addWidget(self.task_input, 1)
        quick_add.addWidget(self.add_task_btn)
        tasks_layout.addLayout(quick_add)

        self.quick_tasks_list = QListWidget()
        self.quick_tasks_list.setAlternatingRowColors(True)
        self.quick_tasks_list.setStyleSheet("font-size: 13px;")
        tasks_layout.addWidget(self.quick_tasks_list, 1)

        quick_actions = QHBoxLayout()
        self.remove_task_btn = QPushButton("Remove Selected")
        self.remove_task_btn.clicked.connect(self.remove_selected_quick_task)
        self.clear_tasks_btn = QPushButton("Clear All")
        self.clear_tasks_btn.clicked.connect(self.quick_tasks_list.clear)
        quick_actions.addWidget(self.remove_task_btn)
        quick_actions.addWidget(self.clear_tasks_btn)
        quick_actions.addStretch()
        tasks_layout.addLayout(quick_actions)
        self.workspace_split.addWidget(self.tasks_group)

        self.workspace_split.setSizes([1, 1])
        layout.addWidget(self.workspace_split, 1)

        self._apply_layout_density()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_layout_density()

    def _apply_layout_density(self, viewport_height=None):
        if viewport_height is None:
            if hasattr(self, "scroll_area") and self.scroll_area.viewport():
                viewport_height = self.scroll_area.viewport().height()
            else:
                viewport_height = self.height()

        compact_threshold = 900 if self._is_windows else 780
        compact_mode = viewport_height > 0 and viewport_height < compact_threshold

        if compact_mode == self._compact_mode_active:
            return
        self._compact_mode_active = compact_mode

        if compact_mode:
            self.main_content_layout.setContentsMargins(14, 8, 14, 8)
            self.main_content_layout.setSpacing(10)
            self.status_label.setStyleSheet("font-size: 20px; color: #f44336; font-weight: bold;")
            self.timer_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #eeeeee;")
            self.vu_meter.setFixedSize(320, 16)
            self.notes_input.setMinimumHeight(160)
            self.pause_btn.setFixedSize(112, 44)
            self.stop_btn.setFixedSize(112, 44)
            self.cancel_btn.setFixedSize(112, 44)
            self.workspace_split.setOrientation(Qt.Orientation.Vertical)
        else:
            self.main_content_layout.setContentsMargins(20, 14, 20, 14)
            self.main_content_layout.setSpacing(14)
            self.status_label.setStyleSheet("font-size: 24px; color: #f44336; font-weight: bold;")
            self.timer_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #eeeeee;")
            self.vu_meter.setFixedSize(400, 20)
            self.notes_input.setMinimumHeight(220)
            self.pause_btn.setFixedSize(124, 50)
            self.stop_btn.setFixedSize(124, 50)
            self.cancel_btn.setFixedSize(124, 50)
            self.workspace_split.setOrientation(Qt.Orientation.Horizontal)

    def add_quick_task(self):
        text = self.task_input.text().strip()
        if not text:
            return
        self.quick_tasks_list.addItem(QListWidgetItem(text))
        self.task_input.clear()

    def remove_selected_quick_task(self):
        for item in self.quick_tasks_list.selectedItems():
            row = self.quick_tasks_list.row(item)
            self.quick_tasks_list.takeItem(row)

    def get_quick_tasks(self):
        tasks = []
        for i in range(self.quick_tasks_list.count()):
            item = self.quick_tasks_list.item(i)
            if item:
                text = item.text().strip()
                if text:
                    tasks.append(text)
        return tasks

    def start_recording(self):
        try:
            logging.info("RecordingInProgressWidget.start_recording called")
            if not self.recorder.is_recording:
                self.recorder.start()
            self.recording_started = True
            self.timer.start(1000)
            logging.info(
                "Recording started: is_recording=%s fs=%s channels=%s",
                self.recorder.is_recording,
                getattr(self.recorder, "fs", "?"),
                getattr(self.recorder, "channels", "?"),
            )
        except Exception as e:
            logging.exception("Failed to start recording in RecordingInProgressWidget.")
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
        if self._is_finishing:
            logging.warning("finish_recording ignored because _is_finishing is already True.")
            return
        self._is_finishing = True
        self.timer.stop()
        logging.info(
            "finish_recording started: recording_started=%s recorder.is_recording=%s duration_seconds=%s",
            self.recording_started,
            getattr(self.recorder, "is_recording", None),
            self.duration_seconds,
        )
        if not self.recording_started:
            # If recording never started, just cancel
            logging.warning("finish_recording called without active recording; emitting cancelled.")
            self.cleanup()
            self.cancelled.emit()
            self._is_finishing = False
            return
        try:
            file_path = self.recorder.stop()
            logging.info("recorder.stop() returned path=%s", file_path)
        except Exception:
            logging.exception("Exception while stopping recorder.")
            file_path = None
        self.recording_started = False
        self.cleanup()
        if file_path:
            # Build final config with user inputs
            final_config = {
                **self.config,
                "title": self.title_input.text().strip(),
                "tags": self.tags_input.text().strip(),
                "recording_notes": self.notes_input.toPlainText().strip(),
                "pending_tasks": self.get_quick_tasks(),
                "model": self.model_combo.currentText(),
                "diarization": self.diarization_check.isChecked(),
                "auto_summarize_after_transcription": self.auto_summary_check.isChecked(),
            }
            logging.info(
                "Recording finished. Emitting finished signal with file=%s title=%s model=%s diarization=%s auto_summary=%s pending_tasks=%d",
                file_path,
                final_config.get("title", ""),
                final_config.get("model", ""),
                final_config.get("diarization", False),
                final_config.get("auto_summarize_after_transcription", False),
                len(final_config.get("pending_tasks") or []),
            )
            self._save_last_run_config()
            self.finished.emit(file_path, final_config)
        else:
            logging.error("Recording stop did not produce an audio file. Emitting cancelled.")
            self.cancelled.emit()
        self._is_finishing = False

    def cancel_recording(self):
        self.timer.stop()
        if self.recording_started:
            try:
                self.recorder.stop()
            except Exception:
                pass  # Ignore errors when cancelling
        self.recording_started = False
        self.cleanup()
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

    def cleanup(self):
        self.timer.stop()
        if self._amplitude_connected:
            try:
                self.recorder.amplitude_changed.disconnect(self.update_vu_meter)
            except Exception:
                pass
            self._amplitude_connected = False

    def _save_last_run_config(self, *args):
        self.settings.setValue("rec_config/model", self.model_combo.currentText())
        self.settings.setValue("rec_config/diarization", self.diarization_check.isChecked())
        self.settings.setValue(
            "rec_config/auto_summarize_after_transcription",
            self.auto_summary_check.isChecked(),
        )

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
