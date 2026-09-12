"""Safety policy and platform notifications for an active recording."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from src.ui.recording_in_progress.session import format_elapsed_time


def recording_tray_icon():
    """Use the application's branded icon, with a Qt icon as a safe fallback."""
    app_icon = QApplication.windowIcon()
    if not app_icon.isNull():
        return app_icon
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    logo_icon = QIcon(str(base_path / "logo.png"))
    if not logo_icon.isNull():
        return logo_icon
    return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)


@dataclass(frozen=True)
class RecordingGuardianSettings:
    """User-controlled safety policy. Automatic silence stopping is opt-in."""

    duration_reminder_seconds: int = 3600
    silence_warning_seconds: int = 900
    duration_reminders_enabled: bool = True
    silence_warnings_enabled: bool = True
    tray_notifications_enabled: bool = True
    auto_stop_after_silence: bool = False
    activity_amplitude_threshold: float = 0.01

    @classmethod
    def from_settings(cls, settings):
        return cls(
            duration_reminder_seconds=max(
                1, int(settings.value("recording_guardian/duration_reminder_seconds", 3600))
            ),
            silence_warning_seconds=max(
                1, int(settings.value("recording_guardian/silence_warning_seconds", 900))
            ),
            duration_reminders_enabled=settings.value(
                "recording_guardian/duration_reminders_enabled", True, type=bool
            ),
            silence_warnings_enabled=settings.value(
                "recording_guardian/silence_warnings_enabled", True, type=bool
            ),
            tray_notifications_enabled=settings.value(
                "recording_guardian/tray_notifications_enabled", True, type=bool
            ),
            auto_stop_after_silence=settings.value(
                "recording_guardian/auto_stop_after_silence", False, type=bool
            ),
            activity_amplitude_threshold=float(
                settings.value("recording_guardian/activity_amplitude_threshold", 0.01)
            ),
        )


class SystemTrayPort(QObject):
    """Availability-aware Qt tray adapter; harmless on unsupported desktops. Proxies to SystemTrayManager."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = None
        
    def _get_manager(self):
        if self._manager:
            return self._manager
        app = QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if hasattr(widget, "system_tray_manager"):
                    self._manager = widget.system_tray_manager
                    return self._manager
        return None

    def start(self, stop_callback, pause_callback, cancel_callback):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return False
        
        manager = self._get_manager()
        if manager:
            manager.bind_recording_actions(stop_callback, pause_callback, cancel_callback)
            self.update_duration(0)
            return True
        return False

    def update_duration(self, elapsed_seconds):
        manager = self._get_manager()
        if manager:
            manager.set_recording_tooltip(f"Recording in progress — {format_elapsed_time(elapsed_seconds)}")

    def set_paused(self, paused):
        manager = self._get_manager()
        if manager:
            manager.set_recording_paused(paused)

    def notify(self, title, message):
        manager = self._get_manager()
        if manager:
            manager.show_message(title, message)
            return True
        return False

    def cleanup(self):
        manager = self._get_manager()
        if manager:
            manager.unbind_recording_actions()


class RecordingSafetyGuardian(QObject):
    """Observe one capture lifecycle without ever owning audio persistence."""

    notification_requested = pyqtSignal(str, str)
    status_changed = pyqtSignal(str)
    stop_requested = pyqtSignal()

    def __init__(self, settings, tray_port=None, parent=None):
        super().__init__(parent)
        self.policy = RecordingGuardianSettings.from_settings(settings)
        self.tray_port = tray_port or SystemTrayPort(self)
        self.active = False
        self.elapsed_seconds = 0
        self._next_duration_reminder = self.policy.duration_reminder_seconds
        self._last_activity_second = 0
        self._silence_warned = False
        self._auto_stop_dispatched = False

    def start(self, stop_callback, pause_callback, cancel_callback):
        self.active = True
        self.elapsed_seconds = 0
        self._next_duration_reminder = self.policy.duration_reminder_seconds
        self._last_activity_second = 0
        self._silence_warned = False
        self._auto_stop_dispatched = False
        if not self.tray_port.start(stop_callback, pause_callback, cancel_callback):
            self.status_changed.emit("Recording in progress (system tray unavailable).")

    def set_paused(self, paused):
        """Keep the tray action in sync with the existing capture pause state."""
        set_paused = getattr(self.tray_port, "set_paused", None)
        if set_paused is not None:
            set_paused(paused)

    def tick(self, elapsed_seconds):
        if not self.active:
            return
        self.elapsed_seconds = elapsed_seconds
        self.tray_port.update_duration(elapsed_seconds)
        if self.policy.duration_reminders_enabled and elapsed_seconds >= self._next_duration_reminder:
            self._remind(
                "Recording still active",
                f"Recording has been active for {format_elapsed_time(elapsed_seconds)}. "
                "Choose Stop and Save when you are finished.",
            )
            self._next_duration_reminder = elapsed_seconds + self.policy.duration_reminder_seconds
        self._check_silence()

    def record_amplitude(self, amplitude):
        if self.active and amplitude >= self.policy.activity_amplitude_threshold:
            self._last_activity_second = self.elapsed_seconds
            self._silence_warned = False

    def _check_silence(self):
        if not self.policy.silence_warnings_enabled or self._silence_warned:
            return
        if self.elapsed_seconds - self._last_activity_second < self.policy.silence_warning_seconds:
            return
        self._silence_warned = True
        self._remind(
            "No audio detected",
            "No audio activity has been detected. Recording continues until you choose Stop and Save.",
        )
        if self.policy.auto_stop_after_silence and not self._auto_stop_dispatched:
            self._auto_stop_dispatched = True
            self.stop_requested.emit()

    def _remind(self, title, message):
        if self.policy.tray_notifications_enabled:
            self.tray_port.notify(title, message)
        self.notification_requested.emit(title, message)
        self.status_changed.emit(f"{title}: {message}")

    def cleanup(self):
        self.active = False
        self.tray_port.cleanup()
