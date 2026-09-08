# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging
import platform

from PyQt6.QtCore import QSettings, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget

from src.database import DBManager
from src.ui.recording_in_progress.layout import (
    apply_layout_density,
    build_recording_in_progress_layout,
)
from src.ui.recording_in_progress.runtime import RecordingCaptureRuntime
from src.ui.recording_in_progress.session import (
    build_finished_config,
    format_elapsed_time,
    save_last_run_config,
)
from src.ui.recording_in_progress.workspace import (
    add_quick_task,
    quick_task_contents,
    remove_selected_quick_tasks,
)

Recorder = None


class RecordingInProgressWidget(QWidget):
    """Public capture-screen facade for recording tabs and their Qt signals."""

    finished = pyqtSignal(str, dict)
    cancelled = pyqtSignal()

    def __init__(self, recorder=None, config=None, parent=None):
        super().__init__(parent)
        self._is_windows = platform.system() == "Windows"
        self._compact_mode_active = False
        self.recorder = recorder or self._create_recorder()
        self.config = config or {}
        self.recording_started = False
        self._is_finishing = False
        self.db = DBManager()
        self.settings = QSettings("Hectronic", "Secretario")
        self.runtime = RecordingCaptureRuntime(self.recorder, self.update_vu_meter)
        self.runtime.configure(self.config)
        self.duration_seconds = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.init_ui()
        self.start_recording()

    @staticmethod
    def _create_recorder():
        global Recorder
        if Recorder is None:
            from src.audio import Recorder as recorder_class
            Recorder = recorder_class
        return Recorder()

    def init_ui(self):
        build_recording_in_progress_layout(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_layout_density()

    def _apply_layout_density(self, viewport_height=None):
        apply_layout_density(self, self._is_windows, viewport_height)

    def add_quick_task(self):
        return add_quick_task(self.task_input, self.quick_tasks_list)

    def remove_selected_quick_task(self):
        remove_selected_quick_tasks(self.quick_tasks_list)

    def get_quick_tasks(self):
        return quick_task_contents(self.quick_tasks_list)

    def start_recording(self):
        logging.info("RecordingInProgressWidget.start_recording called")
        error = self.runtime.start()
        if error is None:
            self.recording_started = True
            self.timer.start(1000)
            logging.info("Recording started: is_recording=%s", self.recorder.is_recording)
            return
        self.recording_started = False
        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet("font-size: 18px; color: #f44336; font-weight: bold;")
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

    def toggle_pause(self):
        if not self.recording_started:
            return
        paused = self.runtime.toggle_pause()
        self.pause_btn.setText("Resume" if paused else "Pause")
        self.status_label.setText("Recording Paused" if paused else "Recording in Progress...")
        if paused:
            self.timer.stop()
        else:
            self.timer.start(1000)

    def finish_recording(self):
        if self._is_finishing:
            logging.warning("finish_recording ignored because it is already in progress.")
            return
        self._is_finishing = True
        self.timer.stop()
        try:
            if not self.recording_started:
                self.cleanup()
                self.cancelled.emit()
                return
            file_path = self.runtime.stop()
            self.recording_started = False
            self.cleanup()
            if not file_path:
                logging.error("Recording stop did not produce an audio file.")
                self.cancelled.emit()
                return
            final_config = build_finished_config(
                self.config,
                title=self.title_input.text(),
                tags=self.tags_input.text(),
                recording_notes=self.notes_input.toPlainText(),
                pending_tasks=self.get_quick_tasks(),
                model=self.model_combo.currentText(),
                diarization=self.diarization_check.isChecked(),
                auto_summarize_after_transcription=self.auto_summary_check.isChecked(),
            )
            self._save_last_run_config()
            self.finished.emit(file_path, final_config)
        finally:
            self._is_finishing = False

    def cancel_recording(self):
        self.timer.stop()
        self.runtime.cancel(self.recording_started)
        self.recording_started = False
        self.cleanup()
        self.cancelled.emit()

    def update_timer(self):
        self.duration_seconds += 1
        self.timer_label.setText(format_elapsed_time(self.duration_seconds))

    def update_vu_meter(self, amplitude):
        self.vu_meter.setValue(min(100, int(amplitude * 1000)))

    def cleanup(self):
        self.timer.stop()
        self.runtime.cleanup()

    def _save_last_run_config(self, *_args):
        save_last_run_config(
            self.settings,
            model=self.model_combo.currentText(),
            diarization=self.diarization_check.isChecked(),
            auto_summarize_after_transcription=self.auto_summary_check.isChecked(),
        )

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
