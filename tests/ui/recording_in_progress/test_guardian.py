from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QIcon

from src.ui.recording_in_progress.guardian import RecordingSafetyGuardian, recording_tray_icon


class _TrayPort:
    def __init__(self, available=True):
        self.available = available
        self.callback = None
        self.durations = []
        self.notifications = []
        self.cleaned = False

    def start(self, stop_callback, pause_callback, cancel_callback):
        self.callback = stop_callback
        self.pause_callback = pause_callback
        self.cancel_callback = cancel_callback
        return self.available

    def update_duration(self, seconds):
        self.durations.append(seconds)

    def notify(self, title, message):
        self.notifications.append((title, message))
        return self.available

    def cleanup(self):
        self.cleaned = True


def _settings(tmp_path, **values):
    settings = QSettings(str(tmp_path / "guardian.ini"), QSettings.Format.IniFormat)
    for key, value in values.items():
        settings.setValue(key.replace("__", "/"), value)
    return settings


def test_recording_tray_icon_uses_the_application_brand_or_safe_fallback(qtbot):
    icon = recording_tray_icon()
    assert isinstance(icon, QIcon)
    assert icon.isNull() is False


def test_guardian_updates_tray_and_rate_limits_duration_reminders(qtbot, tmp_path):
    settings = _settings(tmp_path, recording_guardian__duration_reminder_seconds=10)
    tray = _TrayPort()
    guardian = RecordingSafetyGuardian(settings, tray_port=tray)
    reminders = []
    guardian.notification_requested.connect(lambda title, message: reminders.append((title, message)))

    guardian.start(lambda: None, lambda: None, lambda: None)
    guardian.tick(10)
    guardian.tick(11)
    guardian.tick(20)
    guardian.cleanup()

    assert tray.durations == [10, 11, 20]
    assert [title for title, _ in reminders] == ["Recording still active", "Recording still active"]
    assert tray.cleaned is True


def test_guardian_warns_for_silence_but_never_stops_by_default(qtbot, tmp_path):
    settings = _settings(tmp_path, recording_guardian__silence_warning_seconds=5)
    tray = _TrayPort(available=False)
    guardian = RecordingSafetyGuardian(settings, tray_port=tray)
    stops = []
    statuses = []
    guardian.stop_requested.connect(lambda: stops.append(True))
    guardian.status_changed.connect(statuses.append)

    guardian.start(lambda: None, lambda: None, lambda: None)
    guardian.tick(5)
    guardian.tick(20)

    assert [title for title, _ in tray.notifications] == ["No audio detected"]
    assert stops == []
    assert statuses[0] == "Recording in progress (system tray unavailable)."


def test_guardian_resets_silence_after_activity_and_honors_explicit_auto_stop(qtbot, tmp_path):
    settings = _settings(
        tmp_path,
        recording_guardian__silence_warning_seconds=5,
        recording_guardian__auto_stop_after_silence=True,
    )
    guardian = RecordingSafetyGuardian(settings, tray_port=_TrayPort())
    stops = []
    guardian.stop_requested.connect(lambda: stops.append(True))

    guardian.start(lambda: None, lambda: None, lambda: None)
    guardian.tick(4)
    guardian.record_amplitude(0.2)
    guardian.tick(8)
    assert stops == []
    guardian.tick(9)

    assert stops == [True]


def test_guardian_can_disable_reminders_and_tray_notifications(qtbot, tmp_path):
    settings = _settings(
        tmp_path,
        recording_guardian__duration_reminder_seconds=1,
        recording_guardian__silence_warning_seconds=1,
        recording_guardian__duration_reminders_enabled=False,
        recording_guardian__silence_warnings_enabled=False,
        recording_guardian__tray_notifications_enabled=False,
    )
    tray = _TrayPort()
    guardian = RecordingSafetyGuardian(settings, tray_port=tray)

    guardian.start(lambda: None, lambda: None, lambda: None)
    guardian.tick(5)

    assert tray.notifications == []
