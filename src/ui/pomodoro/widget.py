"""Focused-work controls; application service owns the timer."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from src.app.pomodoro.audio_notes import AudioNoteCapture
from src.audio import Recorder


class PomodoroWidget(QWidget):
    activity_changed = pyqtSignal()

    def __init__(self, service, persistence, *, break_service=None, settings=None, recorder=None,
                 audio_dir=None, capture_available=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.break_service = break_service
        self.db = persistence
        self.settings = settings or QSettings("Hectronic", "Secretario")
        self.capture_available = capture_available or (lambda: True)
        self.audio = AudioNoteCapture(recorder or Recorder(), persistence,
                                      storage_dir=audio_dir or Path.cwd() / "productivity_audio")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("What are you focusing on?")
        if self.service._session:
            self.title_input.setText(self.service._session["title"])
        form.addRow("Title", self.title_input)
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Comma-separated tags")
        if self.service._session:
            self.tags_input.setText(", ".join(self.service._session["tags"]))
        form.addRow("Tags", self.tags_input)
        self.focus_minutes = self._duration(form, "Focus", "pomodoro/focus_minutes", 25)
        self.short_break_minutes = self._duration(form, "Short break", "pomodoro/short_break_minutes", 5)
        self.long_break_minutes = self._duration(form, "Long break", "pomodoro/long_break_minutes", 15)
        self.tray_notifications = QCheckBox("Notify from the system tray when focus ends")
        self.tray_notifications.setChecked(self.settings.value("pomodoro/tray_notifications", True, type=bool))
        self.tray_notifications.toggled.connect(lambda checked: self.settings.setValue("pomodoro/tray_notifications", checked))
        form.addRow("Notifications", self.tray_notifications)
        layout.addLayout(form)

        self.time_label = QLabel()
        layout.addWidget(self.time_label)
        controls = QHBoxLayout()
        self.start_button = QPushButton("Start focus")
        self.start_button.clicked.connect(self.start_focus)
        controls.addWidget(self.start_button)
        self.save_metadata_button = QPushButton("Save title/tags")
        self.save_metadata_button.clicked.connect(self.save_metadata)
        controls.addWidget(self.save_metadata_button)
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.toggle_pause)
        controls.addWidget(self.pause_button)
        self.finish_button = QPushButton("Finish early")
        self.finish_button.clicked.connect(self.finish_focus)
        controls.addWidget(self.finish_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_focus)
        controls.addWidget(self.cancel_button)
        layout.addLayout(controls)

        breaks_row = QHBoxLayout()
        self.short_break_button = QPushButton("Start short break")
        self.short_break_button.clicked.connect(lambda: self.start_break("short"))
        breaks_row.addWidget(self.short_break_button)
        self.long_break_button = QPushButton("Start long break")
        self.long_break_button.clicked.connect(lambda: self.start_break("long"))
        breaks_row.addWidget(self.long_break_button)
        self.break_pause_button = QPushButton("Pause break")
        self.break_pause_button.clicked.connect(self.toggle_break_pause)
        breaks_row.addWidget(self.break_pause_button)
        self.break_finish_button = QPushButton("Finish break")
        self.break_finish_button.clicked.connect(self.finish_break)
        breaks_row.addWidget(self.break_finish_button)
        self.break_cancel_button = QPushButton("Cancel break")
        self.break_cancel_button.clicked.connect(self.cancel_break)
        breaks_row.addWidget(self.break_cancel_button)
        layout.addLayout(breaks_row)
        self.break_label = QLabel()
        layout.addWidget(self.break_label)

        layout.addWidget(QLabel("Notes"))
        self.note_title = QLineEdit()
        self.note_title.setPlaceholderText("Note title")
        layout.addWidget(self.note_title)
        self.note_tags = QLineEdit()
        self.note_tags.setPlaceholderText("Note tags, comma-separated")
        layout.addWidget(self.note_tags)
        self.note_body = QTextEdit()
        self.note_body.setPlaceholderText("Write a note during or outside a Pomodoro")
        layout.addWidget(self.note_body)
        notes_row = QHBoxLayout()
        self.save_note_button = QPushButton("Save text note")
        self.save_note_button.clicked.connect(self.save_text_note)
        notes_row.addWidget(self.save_note_button)
        self.audio_button = QPushButton("Record audio note")
        self.audio_button.clicked.connect(self.toggle_audio_note)
        notes_row.addWidget(self.audio_button)
        self.cancel_audio_button = QPushButton("Cancel audio note")
        self.cancel_audio_button.clicked.connect(self.cancel_audio_note)
        self.cancel_audio_button.setEnabled(False)
        notes_row.addWidget(self.cancel_audio_button)
        self.transcribe_audio = QCheckBox("Transcribe audio note")
        notes_row.addWidget(self.transcribe_audio)
        layout.addLayout(notes_row)
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        self._audio_transcription = None
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self.refresh)
        self._clock_timer.start(250)
        self.refresh()

    def _duration(self, form, label, key, default):
        spin = QSpinBox()
        spin.setRange(1, 240)
        try:
            value = int(self.settings.value(key, default))
        except (TypeError, ValueError):
            value = default
        spin.setValue(min(240, max(1, value)))
        spin.valueChanged.connect(lambda value, setting_key=key: self.settings.setValue(setting_key, value))
        form.addRow(f"{label} minutes", spin)
        return spin

    def _linked_id(self):
        return self.service.pomodoro_id if self.service.state in ("running", "paused") else None

    def _show_error(self, error):
        self.status_label.setText(str(error))

    def start_focus(self):
        try:
            if self.break_service and self.break_service.state in ("running", "paused"):
                raise RuntimeError("Finish or cancel the break before starting focus")
            if self.service.state in ("running", "paused"):
                box = QMessageBox(self)
                box.setWindowTitle("Active Pomodoro")
                box.setText("Finish or cancel the current interval before starting another?")
                finish = box.addButton("Finish early", QMessageBox.ButtonRole.AcceptRole)
                cancel = box.addButton("Cancel current", QMessageBox.ButtonRole.DestructiveRole)
                box.addButton("Keep current", QMessageBox.ButtonRole.RejectRole)
                box.exec()
                if box.clickedButton() is finish:
                    self.service.finish()
                elif box.clickedButton() is cancel:
                    self.service.cancel()
                else:
                    return
            self.service.start(self.title_input.text(), self.tags_input.text(), self.focus_minutes.value() * 60)
            self.status_label.setText("Focus started")
            self.activity_changed.emit()
            self.refresh()
        except Exception as error:
            self._show_error(error)

    def save_metadata(self):
        try:
            self.service.update_metadata(self.title_input.text(), self.tags_input.text())
            self.status_label.setText("Title and tags saved")
            self.activity_changed.emit()
        except Exception as error:
            self._show_error(error)

    def start_break(self, kind):
        if not self.break_service:
            return
        try:
            duration = self.short_break_minutes.value() if kind == "short" else self.long_break_minutes.value()
            self.break_service.start(kind, duration * 60)
            self.status_label.setText(f"{kind.capitalize()} break started")
            self.refresh()
        except Exception as error:
            self._show_error(error)

    def toggle_break_pause(self):
        if not self.break_service:
            return
        if self.break_service.state == "running":
            self.break_service.pause()
        elif self.break_service.state == "paused":
            self.break_service.resume()
        self.refresh()

    def finish_break(self):
        if self.break_service and self.break_service.finish():
            self.status_label.setText("Break completed")
            self.activity_changed.emit()
        self.refresh()

    def cancel_break(self):
        if self.break_service and self.break_service.cancel():
            self.status_label.setText("Break cancelled")
        self.refresh()

    def toggle_pause(self):
        try:
            if self.service.state == "running":
                self.service.pause()
            elif self.service.state == "paused":
                self.service.resume()
            self.refresh()
        except Exception as error:
            self._show_error(error)

    def finish_focus(self):
        try:
            if self.service.finish():
                self.status_label.setText("Pomodoro completed")
                self.activity_changed.emit()
            self.refresh()
        except Exception as error:
            self._show_error(error)

    def cancel_focus(self):
        if self.service.state not in ("running", "paused"):
            return
        answer = QMessageBox.question(self, "Cancel Pomodoro", "Discard this focus interval? Saved notes remain.",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.service.cancel()
            self.status_label.setText("Pomodoro cancelled; saved notes remain")
            self.activity_changed.emit()
            self.refresh()

    def save_text_note(self):
        try:
            self.db.create_productivity_note("text", self.note_title.text(), self.note_tags.text(),
                                             body=self.note_body.toPlainText(), pomodoro_id=self._linked_id())
            self.note_title.clear()
            self.note_body.clear()
            self.status_label.setText("Text note saved")
            self.activity_changed.emit()
        except Exception as error:
            self._show_error(error)

    def toggle_audio_note(self):
        try:
            if not self.audio.active:
                if not self.note_title.text().strip():
                    raise ValueError("Enter an audio-note title first")
                if not self.capture_available():
                    raise RuntimeError("Another recording is active. Finish it before recording an audio note")
                self._configure_audio_input()
                self.audio.start()
                self.audio_button.setText("Stop and save audio note")
                self.cancel_audio_button.setEnabled(True)
                self.status_label.setText("Recording audio note")
                return
            note_id = self.audio.stop_and_save(self.note_title.text(), self.note_tags.text(), self._linked_id())
            self.audio_button.setText("Record audio note")
            self.cancel_audio_button.setEnabled(False)
            self.note_title.clear()
            self.status_label.setText("Audio note saved")
            self.activity_changed.emit()
            if self.transcribe_audio.isChecked():
                self._start_transcription(note_id)
        except Exception as error:
            self.audio_button.setText("Record audio note" if not self.audio.active else "Stop and save audio note")
            self.cancel_audio_button.setEnabled(self.audio.active)
            self._show_error(error)

    def cancel_audio_note(self):
        try:
            self.audio.cancel()
            self.status_label.setText("Audio note discarded; Pomodoro continues")
        except Exception as error:
            self._show_error(error)
        finally:
            self.audio_button.setText("Record audio note")
            self.cancel_audio_button.setEnabled(False)

    def _configure_audio_input(self):
        recorder = self.audio.recorder
        if not hasattr(recorder, "set_device"):
            return
        index = self.settings.value("default_mic_index", None)
        name = self.settings.value("default_mic_name", "")
        prefer_index = self.settings.value("audio_prefer_device_index", False, type=bool)
        if not prefer_index and name and hasattr(recorder, "get_input_devices"):
            match = next((device_id for device_id, label in recorder.get_input_devices() if label == name), None)
            if match is not None:
                recorder.set_device(match)
                return
        if index is not None:
            try:
                recorder.set_device(int(index))
            except (TypeError, ValueError):
                pass

    def _start_transcription(self, note_id):
        from src.ui.notebooks.transcription_runtime import NotebookTranscriptionRuntime
        if self._audio_transcription is None:
            self._audio_transcription = NotebookTranscriptionRuntime()
        note = self.db.fetch_productivity_note(note_id)
        result = self._audio_transcription.start(
            note["audio_ref"],
            lambda response: self._on_transcribed(note_id, response),
            lambda error: self._on_transcription_error(note_id, error),
        )
        if result.preflight_error:
            self.status_label.setText(result.preflight_error)

    def _on_transcribed(self, note_id, result):
        self.db.update_productivity_note_transcription(note_id, result.get("text", ""))
        self.status_label.setText("Audio note transcribed")

    def _on_transcription_error(self, note_id, error):
        self.status_label.setText(f"Audio note transcription failed: {error}")

    def refresh(self):
        state = self.service.state
        remaining = int(self.service.remaining_seconds + 0.999)
        self.time_label.setText(f"{state.capitalize()} · {remaining // 60:02d}:{remaining % 60:02d} remaining")
        self.pause_button.setEnabled(state in ("running", "paused"))
        self.pause_button.setText("Resume" if state == "paused" else "Pause")
        self.finish_button.setEnabled(state in ("running", "paused"))
        self.cancel_button.setEnabled(state in ("running", "paused"))
        self.start_button.setText("Start new focus" if state in ("running", "paused") else "Start focus")
        self.save_metadata_button.setEnabled(state in ("running", "paused"))
        if self.break_service:
            break_state = self.break_service.state
            active = break_state in ("running", "paused")
            self.short_break_button.setEnabled(not active and state not in ("running", "paused"))
            self.long_break_button.setEnabled(not active and state not in ("running", "paused"))
            self.break_pause_button.setEnabled(active)
            self.break_pause_button.setText("Resume break" if break_state == "paused" else "Pause break")
            self.break_finish_button.setEnabled(active)
            self.break_cancel_button.setEnabled(active)
            rest = int(self.break_service.remaining_seconds + 0.999)
            self.break_label.setText(f"Break {break_state} · {rest // 60:02d}:{rest % 60:02d} remaining")
        else:
            for button in (self.short_break_button, self.long_break_button,
                           self.break_pause_button, self.break_finish_button, self.break_cancel_button):
                button.setEnabled(False)

    def cleanup(self):
        self._clock_timer.stop()
        self.audio.cancel()
        if self._audio_transcription:
            self._audio_transcription.cleanup()
