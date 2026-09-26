"""Validated editor for recurring meeting templates."""

from __future__ import annotations

from datetime import date
from zoneinfo import available_timezones

from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QSpinBox, QTimeEdit, QVBoxLayout, QWidget,
)

from src.app.scheduling.recurrence import next_occurrences, validate_template


WEEKDAYS = (("Mon", 0), ("Tue", 1), ("Wed", 2), ("Thu", 3), ("Fri", 4), ("Sat", 5), ("Sun", 6))


class MeetingTemplateDialog(QDialog):
    def __init__(self, template=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recurring meeting")
        self._template = template or {}
        self.result_data = None
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.title_edit = QLineEdit(self._template.get("title", ""))
        self.tags_edit = QLineEdit(", ".join(self._template.get("tags", [])))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime.fromString(self._template.get("local_start_time", "09:00"), "HH:mm"))
        self.timezone_combo = QComboBox()
        self.timezone_combo.addItems(sorted(available_timezones()))
        timezone_index = self.timezone_combo.findText(self._template.get("timezone", "Europe/Madrid"))
        self.timezone_combo.setCurrentIndex(max(0, timezone_index))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 1440)
        self.duration_spin.setSuffix(" min")
        self.duration_spin.setValue(max(1, int(self._template.get("expected_duration_seconds", 3600)) // 60))
        self.reminder_spin = QSpinBox()
        self.reminder_spin.setRange(0, 10080)
        self.reminder_spin.setSuffix(" min before")
        self.reminder_spin.setValue(int(self._template.get("reminder_lead_seconds", 600)) // 60)
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Daily", "daily")
        self.kind_combo.addItem("Weekly", "weekly")
        self.kind_combo.addItem("Monthly", "monthly")
        kind_index = self.kind_combo.findData(self._template.get("recurrence_kind", "weekly"))
        self.kind_combo.setCurrentIndex(max(0, kind_index))
        self.kind_combo.currentIndexChanged.connect(self._update_recurrence_controls)
        self.weekdays_widget = QWidget()
        weekday_layout = QHBoxLayout(self.weekdays_widget)
        weekday_layout.setContentsMargins(0, 0, 0, 0)
        saved_days = set((self._template.get("recurrence_payload") or {}).get("weekdays", [0, 1, 2, 3, 4]))
        self.weekday_checks = []
        for label, day in WEEKDAYS:
            check = QCheckBox(label)
            check.setChecked(day in saved_days)
            weekday_layout.addWidget(check)
            self.weekday_checks.append((day, check))
        self.monthly_day_spin = QSpinBox()
        self.monthly_day_spin.setRange(1, 31)
        self.monthly_day_spin.setValue(int((self._template.get("recurrence_payload") or {}).get("day", 1)))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(__import__("PyQt6.QtCore", fromlist=["QDate"]).QDate.fromString(
            self._template.get("starts_on", date.today().isoformat()), "yyyy-MM-dd"))
        self.end_enabled = QCheckBox("Set end date")
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_enabled.setChecked(bool(self._template.get("ends_on")))
        self.end_date_edit.setEnabled(self.end_enabled.isChecked())
        if self._template.get("ends_on"):
            self.end_date_edit.setDate(__import__("PyQt6.QtCore", fromlist=["QDate"]).QDate.fromString(self._template["ends_on"], "yyyy-MM-dd"))
        self.end_enabled.toggled.connect(self.end_date_edit.setEnabled)
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 10000)
        self.limit_spin.setSpecialValueText("No limit")
        self.limit_spin.setValue(int(self._template.get("occurrence_limit") or 0))

        for label, control in (
            ("Title", self.title_edit), ("Tags", self.tags_edit), ("Local start time", self.time_edit),
            ("Time zone", self.timezone_combo), ("Expected duration", self.duration_spin),
            ("Reminder", self.reminder_spin), ("Repeat", self.kind_combo),
            ("Weekdays", self.weekdays_widget), ("Day of month", self.monthly_day_spin),
            ("Starts on", self.start_date_edit), ("Ends on", self._end_widget()),
            ("Occurrence limit", self.limit_spin),
        ):
            form.addRow(label, control)
        layout.addLayout(form)
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        layout.addWidget(self.preview_label)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #c62828")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._update_recurrence_controls()
        for control in (self.time_edit, self.timezone_combo, self.kind_combo, self.start_date_edit,
                        self.monthly_day_spin, self.duration_spin, self.reminder_spin):
            if hasattr(control, "timeChanged"):
                control.timeChanged.connect(self._update_preview)
            elif hasattr(control, "currentIndexChanged"):
                control.currentIndexChanged.connect(self._update_preview)
            elif hasattr(control, "dateChanged"):
                control.dateChanged.connect(self._update_preview)
            elif hasattr(control, "valueChanged"):
                control.valueChanged.connect(self._update_preview)
        self._update_preview()

    def _end_widget(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.end_enabled)
        layout.addWidget(self.end_date_edit)
        return widget

    def _update_recurrence_controls(self, *_args):
        kind = self.kind_combo.currentData()
        self.weekdays_widget.setVisible(kind == "weekly")
        self.monthly_day_spin.setVisible(kind == "monthly")
        self._update_preview()

    def _payload(self):
        kind = self.kind_combo.currentData()
        payload = {"version": 1}
        if kind == "weekly":
            payload["weekdays"] = [day for day, check in self.weekday_checks if check.isChecked()]
        elif kind == "monthly":
            payload["day"] = self.monthly_day_spin.value()
        return {
            "title": self.title_edit.text(), "tags": self.tags_edit.text(),
            "timezone": self.timezone_combo.currentText(),
            "local_start_time": self.time_edit.time().toString("HH:mm"),
            "expected_duration_seconds": self.duration_spin.value() * 60,
            "reminder_lead_seconds": self.reminder_spin.value() * 60,
            "recurrence_kind": kind, "recurrence_payload": payload,
            "starts_on": self.start_date_edit.date().toString("yyyy-MM-dd"),
            "ends_on": self.end_date_edit.date().toString("yyyy-MM-dd") if self.end_enabled.isChecked() else None,
            "occurrence_limit": self.limit_spin.value() or None,
            "enabled": bool(self._template.get("enabled", True)),
        }

    def _update_preview(self, *_args):
        try:
            rows = next_occurrences(validate_template(self._payload()), count=3)
            self.preview_label.setText("Next occurrences: " + " · ".join(
                f"{row['scheduled_local']} ({row['timezone']})" for row in rows
            ))
        except (ValueError, TypeError, KeyError):
            self.preview_label.setText("Next occurrences will appear after the recurrence is valid.")

    def _save(self):
        try:
            self.result_data = validate_template(self._payload())
        except (ValueError, TypeError) as error:
            self.error_label.setText(str(error))
            return
        self.accept()
