"""Productivity preferences owned by Settings and consumed by Pomodoro UI."""

from PyQt6.QtWidgets import QCheckBox, QFormLayout, QLabel, QSpinBox, QVBoxLayout, QWidget


class ProductivitySettingsPanel(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        form = QFormLayout()
        self.focus_minutes = self._duration(form, "Focus interval", "pomodoro/focus_minutes", 25)
        self.short_break_minutes = self._duration(form, "Short break", "pomodoro/short_break_minutes", 5)
        self.long_break_minutes = self._duration(form, "Long break", "pomodoro/long_break_minutes", 15)
        self.tray_notifications = QCheckBox("Notify from the system tray when a focus interval ends")
        self.tray_notifications.setChecked(settings.value("pomodoro/tray_notifications", True, type=bool))
        form.addRow("Notifications:", self.tray_notifications)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Default durations and completion notifications used by the Pomodoro workflow."))
        layout.addLayout(form)
        layout.addStretch(1)

    def _duration(self, form, label, key, default):
        spin = QSpinBox()
        spin.setRange(1, 240)
        spin.setSuffix(" minutes")
        try:
            value = int(self.settings.value(key, default))
        except (TypeError, ValueError):
            value = default
        spin.setValue(min(240, max(1, value)))
        form.addRow(label + ":", spin)
        return spin

    def save(self):
        self.settings.setValue("pomodoro/focus_minutes", self.focus_minutes.value())
        self.settings.setValue("pomodoro/short_break_minutes", self.short_break_minutes.value())
        self.settings.setValue("pomodoro/long_break_minutes", self.long_break_minutes.value())
        self.settings.setValue("pomodoro/tray_notifications", self.tray_notifications.isChecked())
