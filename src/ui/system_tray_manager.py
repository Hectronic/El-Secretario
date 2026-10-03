"""Qt system-tray façade with state-aware, freshly-dispatched quick actions."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QAction, QPainter, QColor
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu


class SystemTrayManager(QObject):
    """Own the tray icon/menu while feature coordinators own each command."""

    show_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.app = QApplication.instance()
        self._tray_icon = None
        self._menu = None
        self._is_recording = False
        self._action_coordinator = None
        self._recording_callbacks = {}
        self._cleaned = False
        self._init_tray_icon()

    def _init_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logging.warning("System tray is not available on this platform.")
            return
        if self.app:
            self.app.setQuitOnLastWindowClosed(False)

        self._menu = QMenu()
        self.toggle_window_action = self._add_action("toggle_window", "Open app", self._toggle_main_window)
        self._sep_window = self._menu.addSeparator()

        self.recording_status_action = self._add_action("recording_status", "", None)
        self.recording_status_action.setEnabled(False)
        self.start_recording_action = self._add_action("start_recording", "Start recording")
        self.pause_recording_action = self._add_action("pause_recording", "Pause recording")
        self.stop_recording_action = self._add_action("stop_recording", "Stop and save recording")
        self.cancel_recording_action = self._add_action("cancel_recording", "Cancel recording")
        self.open_recording_action = self._add_action("open_recording", "Open recording")
        self._sep_recording = self._menu.addSeparator()

        self.new_text_note_action = self._add_action("new_text_note", "New text note")
        self.new_audio_note_action = self._add_action("new_audio_note", "New audio note")
        self._sep_notes = self._menu.addSeparator()

        self.pomodoro_status_action = self._add_action("pomodoro_status", "", None)
        self.pomodoro_status_action.setEnabled(False)
        self.start_pomodoro_action = self._add_action("start_pomodoro", "Start Pomodoro")
        self.pause_pomodoro_action = self._add_action("toggle_pomodoro", "Pause Pomodoro")
        self.finish_pomodoro_action = self._add_action("finish_pomodoro", "Finish Pomodoro")
        self.cancel_pomodoro_action = self._add_action("cancel_pomodoro", "Cancel Pomodoro")
        self._sep_pomodoro = self._menu.addSeparator()

        self.meeting_status_action = self._add_action("meeting_status", "", None)
        self.meeting_status_action.setEnabled(False)
        self.start_meeting_action = self._add_action("start_meeting", "Start prepared recording")
        self.snooze_meeting_action = self._add_action("snooze_meeting", "Snooze meeting reminder 5 minutes")
        self.dismiss_meeting_action = self._add_action("dismiss_meeting", "Dismiss meeting reminder")
        self.open_meeting_action = self._add_action("open_meeting", "Open meeting details")
        self._sep_meeting = self._menu.addSeparator()

        self.timeline_action = self._add_action("timeline", "Timeline")
        self.tasks_action = self._add_action("tasks", "Tasks")
        self.settings_action = self._add_action("settings", "Settings")
        self._sep_quit = self._menu.addSeparator()
        self.quit_action = self._add_action("quit", "Quit", self._on_quit_triggered)
        self._menu.aboutToShow.connect(self.refresh_menu)

        self._tray_icon = QSystemTrayIcon(self)
        self._update_icon()
        self._tray_icon.setContextMenu(self._menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()
        self.refresh_menu()

    def _add_action(self, command, text, callback=None):
        action = QAction(text, self)
        action.setData(command)
        action.triggered.connect(callback or (lambda _checked=False, key=command: self._trigger_action(key)))
        self._menu.addAction(action)
        return action

    def set_action_coordinator(self, coordinator):
        """Attach the live application command owner after MainWindow bootstrap."""
        self._action_coordinator = coordinator
        self.refresh_menu()

    def _trigger_action(self, command):
        if self._cleaned:
            return False
        coordinator = self._action_coordinator
        if coordinator is not None:
            try:
                payload = self._action_for(command).property("payload")
                result = coordinator.dispatch(command, payload)
            except RuntimeError:
                self.cleanup()
                return False
            self.refresh_menu()
            return result

        callback_names = {
            "pause_recording": "pause",
            "stop_recording": "stop",
            "cancel_recording": "cancel",
        }
        callback = self._recording_callbacks.get(callback_names.get(command, ""))
        if callback is None:
            return False
        try:
            callback()
        except RuntimeError:
            self.unbind_recording_actions()
            return False
        self.refresh_menu()
        return True

    def _action_for(self, command):
        actions = {
            action.data(): action
            for action in self._menu.actions()
            if not action.isSeparator()
        }
        return actions.get(command)

    def refresh_menu(self):
        """Render the current snapshot whenever the user opens the tray menu."""
        if self._menu is None or self._cleaned:
            return
        snapshot = {}
        coordinator = self._action_coordinator
        if coordinator is not None:
            try:
                value = coordinator.snapshot()
                snapshot = value if isinstance(value, dict) else {}
            except RuntimeError:
                self.cleanup()
                return
        recording = bool(snapshot.get("recording_active", self._is_recording))
        self.set_recording_state(recording, refresh=False)
        visible = self.main_window.isVisible()
        self.toggle_window_action.setText("Hide app" if visible else "Open app")

        recording_kind = snapshot.get("recording_kind", "capture")
        controllable = bool(snapshot.get("recording_controllable", self._is_recording))
        elapsed = max(0, int(snapshot.get("recording_elapsed", 0)))
        elapsed_text = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
        if recording:
            status = "Audio note" if recording_kind == "audio_note" else "Recording"
            self.recording_status_action.setText(f"{status} active · {elapsed_text}")
        self.recording_status_action.setVisible(recording)
        self.start_recording_action.setVisible(not recording)
        self.pause_recording_action.setVisible(recording and recording_kind == "capture" and controllable)
        self.pause_recording_action.setText(
            "Resume recording" if snapshot.get("recording_paused", False) else "Pause recording"
        )
        self.stop_recording_action.setVisible(recording and controllable)
        self.cancel_recording_action.setVisible(recording and recording_kind == "capture" and controllable)
        self.open_recording_action.setVisible(recording and controllable)
        self.new_audio_note_action.setVisible(bool(snapshot.get("notebook_available", True)))
        can_capture = bool(snapshot.get("audio_capture_available", not recording))
        self.new_audio_note_action.setEnabled(can_capture)
        self.new_audio_note_action.setToolTip(
            "" if can_capture else "Finish the active audio capture before starting an audio note."
        )
        self._sep_recording.setVisible(True)
        self._sep_notes.setVisible(True)

        pomodoro_available = bool(snapshot.get("pomodoro_available", False))
        pomodoro_active = bool(snapshot.get("pomodoro_active", False))
        recovery = bool(snapshot.get("pomodoro_recovery", False))
        pom_state = snapshot.get("pomodoro_state", "idle")
        if pomodoro_active:
            remaining = max(0, int(snapshot.get("pomodoro_remaining", 0)))
            title = str(snapshot.get("pomodoro_title", "Focus"))
            self.pomodoro_status_action.setText(
                f"Pomodoro · {title} · {remaining // 60:02d}:{remaining % 60:02d} remaining"
            )
        self.pomodoro_status_action.setVisible(pomodoro_available and pomodoro_active)
        self.start_pomodoro_action.setVisible(pomodoro_available and not pomodoro_active)
        self.start_pomodoro_action.setEnabled(
            bool(snapshot.get("pomodoro_can_start", pom_state not in ("running", "paused")))
        )
        self.start_pomodoro_action.setToolTip(
            "Resolve the interrupted session or finish the active break first."
            if recovery or not snapshot.get("pomodoro_can_start", True) else ""
        )
        self.pause_pomodoro_action.setVisible(pomodoro_available and pomodoro_active)
        self.pause_pomodoro_action.setEnabled(not recovery)
        self.pause_pomodoro_action.setText(
            "Resume Pomodoro" if pom_state == "paused" else "Pause Pomodoro"
        )
        self.finish_pomodoro_action.setVisible(pomodoro_available and pomodoro_active)
        self.finish_pomodoro_action.setEnabled(not recovery)
        self.cancel_pomodoro_action.setVisible(pomodoro_available and pomodoro_active)
        self.cancel_pomodoro_action.setEnabled(not recovery)
        self._sep_pomodoro.setVisible(pomodoro_available)

        meeting = snapshot.get("meeting")
        has_meeting = bool(meeting)
        meeting_due = bool(meeting and meeting.get("due"))
        if meeting:
            when = meeting.get("scheduled_local", "")
            title = str(meeting.get("title", "Meeting"))
            self.meeting_status_action.setText(
                f"Meeting due · {title} · {when}" if meeting_due else f"Next meeting · {title} · {when}"
            )
            occurrence_id = int(meeting["id"])
            for action in (self.start_meeting_action, self.snooze_meeting_action,
                           self.dismiss_meeting_action, self.open_meeting_action):
                action.setProperty("payload", occurrence_id)
        self.meeting_status_action.setVisible(has_meeting)
        self.start_meeting_action.setVisible(has_meeting and meeting_due)
        self.start_meeting_action.setEnabled(not recording)
        self.snooze_meeting_action.setVisible(
            has_meeting and meeting_due and bool(meeting.get("snoozable", False))
        )
        self.dismiss_meeting_action.setVisible(has_meeting and meeting_due)
        self.open_meeting_action.setVisible(has_meeting)
        self._sep_meeting.setVisible(has_meeting)

        self._update_tooltip(snapshot, recording, elapsed_text)

    def _update_tooltip(self, snapshot, recording, elapsed_text):
        if not self._tray_icon:
            return
        if recording:
            tooltip = f"El Secretario · Recording in progress · {elapsed_text}"
        elif snapshot.get("pomodoro_active"):
            remaining = max(0, int(snapshot.get("pomodoro_remaining", 0)))
            tooltip = f"El Secretario · Focus active · {remaining // 60:02d}:{remaining % 60:02d} remaining"
        else:
            tooltip = "El Secretario"
        self._tray_icon.setToolTip(tooltip)

    def _update_icon(self):
        if not self._tray_icon:
            return
        base_icon = self.main_window.windowIcon()
        if base_icon.isNull() and self.app:
            base_icon = self.app.windowIcon()
        if self._is_recording:
            self._tray_icon.setToolTip("El Secretario - Recording in Progress")
            pixmap = base_icon.pixmap(64, 64)
            if not pixmap.isNull():
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QColor("red"))
                painter.setPen(Qt.PenStyle.NoPen)
                radius = 12
                painter.drawEllipse(
                    pixmap.width() - radius * 2,
                    pixmap.height() - radius * 2,
                    radius * 2,
                    radius * 2,
                )
                painter.end()
                self._tray_icon.setIcon(QIcon(pixmap))
            else:
                self._tray_icon.setIcon(base_icon)
        else:
            self._tray_icon.setToolTip("El Secretario")
            self._tray_icon.setIcon(base_icon)

    def set_recording_state(self, is_recording: bool, *, refresh=True):
        changed = self._is_recording != bool(is_recording)
        self._is_recording = bool(is_recording)
        if changed:
            self._update_icon()
        if refresh and changed:
            self.refresh_menu()

    def show_message(self, title, message):
        if self._tray_icon:
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information)

    def bind_recording_actions(self, stop_callback, pause_callback, cancel_callback):
        """Compatibility hook used by the recording safety guardian."""
        if self._menu is None or self._cleaned:
            return
        self._recording_callbacks = {
            "stop": stop_callback,
            "pause": pause_callback,
            "cancel": cancel_callback,
        }
        if self._action_coordinator is None:
            self.set_recording_state(True, refresh=False)
            for action in (
                self.pause_recording_action,
                self.stop_recording_action,
                self.cancel_recording_action,
            ):
                action.setVisible(True)
        self.refresh_menu()

    def unbind_recording_actions(self):
        self._recording_callbacks.clear()
        if self._action_coordinator is None:
            self.set_recording_state(False, refresh=False)
            for action in (
                getattr(self, "pause_recording_action", None),
                getattr(self, "stop_recording_action", None),
                getattr(self, "cancel_recording_action", None),
            ):
                if action is not None:
                    action.setVisible(False)
        self.refresh_menu()

    def set_recording_tooltip(self, text):
        if self._tray_icon and not self._cleaned:
            self._tray_icon.setToolTip(text)

    def set_recording_paused(self, paused):
        if hasattr(self, "pause_recording_action"):
            self.pause_recording_action.setText("Resume recording" if paused else "Pause recording")

    def set_focus_status(self, title, remaining_seconds, *, paused=False):
        if self._cleaned or not self._tray_icon or self._is_recording:
            return
        remaining = max(0, int(remaining_seconds))
        title = str(title or "Focus")
        self._tray_icon.setToolTip(
            f"El Secretario · Focus {'paused' if paused else 'active'} · {title} · "
            f"{remaining // 60:02d}:{remaining % 60:02d} remaining"
        )

    def _toggle_main_window(self):
        if self._cleaned:
            return
        if self.main_window.isVisible():
            self.main_window.hide()
            self.toggle_window_action.setText("Open app")
        else:
            self.main_window.showNormal()
            self.main_window.activateWindow()
            self.main_window.raise_()
            self.toggle_window_action.setText("Hide app")

    def _on_tray_activated(self, reason):
        if not self._cleaned and reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_main_window()

    def _on_quit_triggered(self):
        if self._cleaned:
            return
        self.quit_requested.emit()
        self.cleanup()

    def cleanup(self):
        if self._cleaned:
            return
        self._cleaned = True
        self._recording_callbacks.clear()
        self._action_coordinator = None
        if self._menu:
            try:
                self._menu.aboutToShow.disconnect(self.refresh_menu)
            except (TypeError, RuntimeError):
                pass
            for action in self._menu.actions():
                try:
                    action.triggered.disconnect()
                except (TypeError, RuntimeError):
                    pass
            self._menu.clear()
        if self._tray_icon:
            try:
                self._tray_icon.activated.disconnect(self._on_tray_activated)
                self._tray_icon.setContextMenu(None)
                self._tray_icon.hide()
                self._tray_icon.deleteLater()
            except RuntimeError:
                pass
            self._tray_icon = None
