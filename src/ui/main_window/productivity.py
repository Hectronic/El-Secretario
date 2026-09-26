"""Main-window ownership of the focus timer and activity navigation."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QSettings, QTimer, QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTextEdit, QVBoxLayout

from src.app.pomodoro.service import PomodoroService
from src.app.pomodoro.breaks import BreakService
from src.ui.pomodoro.widget import PomodoroWidget
from src.ui.timeline.widget import TimelineWidget
from src.ui.recording_in_progress_widget import RecordingInProgressWidget


class ProductivityCoordinator:
    def __init__(self, window):
        self.window = window
        self.settings = QSettings("Hectronic", "Secretario")
        self.service = PomodoroService(window.db, notify=self._notify)
        self.break_service = BreakService(window.db)
        self.timer = QTimer(window)
        self.timer.timeout.connect(self._tick)
        self.timer.start(250)
        if self.service.recovery_required:
            QTimer.singleShot(0, self._offer_recovery)
        if self.break_service.recovery_required:
            QTimer.singleShot(0, self._offer_break_recovery)

    def _notify(self, title, message):
        self.window.handle_status_message(f"{title}: {message}")
        if self.settings.value("pomodoro/tray_notifications", True, type=bool):
            manager = getattr(self.window, "system_tray_manager", None)
            if manager:
                manager.show_message(title, message)

    def _offer_recovery(self):
        if not self.service.recovery_required:
            return
        box = QMessageBox(self.window)
        box.setWindowTitle("Interrupted Pomodoro")
        box.setText(f"'{self.service.title}' was active when El Secretario last closed. What would you like to do?")
        complete = box.addButton("Complete", QMessageBox.ButtonRole.AcceptRole)
        resume = box.addButton("Resume paused", QMessageBox.ButtonRole.ActionRole)
        discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        box.exec()
        choice = "complete" if box.clickedButton() is complete else "resume" if box.clickedButton() is resume else "discard"
        self.service.confirm_recovery(choice)
        self.refresh_views()

    def _tick(self):
        if not self.service.recovery_required and self.service.tick():
            self.refresh_views()
        if not self.break_service.recovery_required and self.break_service.tick():
            self._notify("Break complete", "Time to return to focus")
            self.refresh_views()
        for index in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(index)
            if isinstance(widget, PomodoroWidget):
                widget.refresh()

    def refresh_views(self):
        refresh_tags = getattr(self.window, "refresh_tag_filter", None)
        if callable(refresh_tags):
            refresh_tags()
        for index in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(index)
            if isinstance(widget, TimelineWidget):
                widget.refresh()
            elif isinstance(widget, PomodoroWidget):
                widget.refresh()

    def open_pomodoro(self):
        for index in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(index)
            if isinstance(widget, PomodoroWidget):
                self.window.central_tabs.setCurrentIndex(index)
                return widget
        widget = PomodoroWidget(self.service, self.window.db, break_service=self.break_service,
                                capture_available=self._capture_available, parent=self.window)
        widget.activity_changed.connect(self.refresh_views)
        index = self.window.central_tabs.addTab(widget, "Pomodoro")
        self.window.central_tabs.setCurrentIndex(index)
        return widget

    def open_timeline(self):
        for index in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(index)
            if isinstance(widget, TimelineWidget):
                self.window.central_tabs.setCurrentIndex(index)
                widget.refresh()
                return widget
        widget = TimelineWidget(self.window.db, parent=self.window)
        widget.source_requested.connect(self.open_source)
        tag = self.window.tag_filter_combo.currentText()
        widget.set_global_filters(self.window.current_week_monday, self.window.current_date_filter, tag)
        index = self.window.central_tabs.addTab(widget, "Timeline")
        self.window.central_tabs.setCurrentIndex(index)
        return widget

    def open_source(self, event_type, source_id):
        if event_type == "break":
            rest = self.window.db.fetch_break(source_id)
            if rest:
                QMessageBox.information(self.window, "Break", f"{rest['kind'].capitalize()} break · {int(rest['elapsed_seconds'])} seconds")
            return
        if event_type == "pomodoro":
            pomodoro = self.window.db.fetch_pomodoro(source_id)
            if not pomodoro:
                return
            dialog = QDialog(self.window)
            dialog.setWindowTitle(pomodoro["title"])
            layout = QVBoxLayout(dialog)
            layout.addWidget(QLabel(f"{pomodoro['state']} · {int(pomodoro['elapsed_seconds'])} seconds focused"))
            for note in self.window.db.fetch_productivity_notes(source_id):
                button = QPushButton(f"{note['kind']}: {note['title']}")
                button.clicked.connect(lambda _checked=False, note_id=note["id"]: self.open_source(f"{note['kind']}_note", note_id))
                layout.addWidget(button)
            delete_button = QPushButton("Delete Pomodoro")
            delete_button.clicked.connect(lambda: self._delete_pomodoro(pomodoro, dialog))
            layout.addWidget(delete_button)
            dialog.exec()
            return
        if event_type not in ("text_note", "audio_note"):
            return
        note = self.window.db.fetch_productivity_note(source_id)
        if not note:
            return
        dialog = QDialog(self.window)
        dialog.setWindowTitle(note["title"])
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(note["captured_at"]))
        if note["kind"] == "text":
            body = QTextEdit(note["body"] or "")
            body.setReadOnly(True)
            layout.addWidget(body)
        else:
            if note["transcription"]:
                transcript = QTextEdit(note["transcription"])
                transcript.setReadOnly(True)
                layout.addWidget(transcript)
            output = QAudioOutput(dialog)
            player = QMediaPlayer(dialog)
            player.setAudioOutput(output)
            player.setSource(QUrl.fromLocalFile(note["audio_ref"]))
            buttons = QHBoxLayout()
            play = QPushButton("Play")
            stop = QPushButton("Stop")
            play.clicked.connect(player.play)
            stop.clicked.connect(player.stop)
            buttons.addWidget(play)
            buttons.addWidget(stop)
            layout.addLayout(buttons)
        delete_button = QPushButton("Delete note")
        delete_button.clicked.connect(lambda: self._delete_note(note, dialog))
        layout.addWidget(delete_button)
        dialog.exec()

    def _delete_note(self, note, dialog):
        answer = QMessageBox.question(dialog, "Delete note", f"Delete '{note['title']}'?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        audio_path = self.window.db.delete_productivity_note(note["id"])
        if audio_path:
            path = Path(audio_path)
            owned_dir = (Path.cwd() / "productivity_audio").resolve()
            if path.parent.resolve() == owned_dir:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    logging.exception("Failed deleting productivity audio file")
        dialog.accept()
        self.refresh_views()

    def _delete_pomodoro(self, pomodoro, dialog):
        answer = QMessageBox.question(dialog, "Delete Pomodoro", f"Delete '{pomodoro['title']}'? Saved notes remain.",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.window.db.delete_pomodoro(pomodoro["id"])
        dialog.accept()
        self.refresh_views()

    def cleanup(self):
        self.timer.stop()
        self.service.checkpoint()
        self.break_service.checkpoint()

    def _capture_available(self):
        if getattr(self.window.recorder, "is_recording", False):
            return False
        for index in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(index)
            if isinstance(widget, RecordingInProgressWidget) and widget.recording_started:
                return False
        return True

    def _offer_break_recovery(self):
        if not self.break_service.recovery_required:
            return
        answer = QMessageBox.question(self.window, "Interrupted break", "Resume the paused break?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        self.break_service.confirm_recovery("resume" if answer == QMessageBox.StandardButton.Yes else "discard")
        self.refresh_views()
