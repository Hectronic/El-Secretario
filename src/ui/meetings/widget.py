"""Template manager and date-oriented view of local meeting occurrences."""

from __future__ import annotations

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCalendarWidget, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from src.app.scheduling.recurrence import next_occurrences
from .template_dialog import MeetingTemplateDialog


class RecurringMeetingsWidget(QWidget):
    start_requested = pyqtSignal(int)
    details_requested = pyqtSignal(int)

    def __init__(self, repository, scheduler, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.scheduler = scheduler
        self.setObjectName("recurringMeetingsWidget")
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Recurring meetings"))
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        templates_panel = QWidget()
        templates_layout = QVBoxLayout(templates_panel)
        templates_layout.addWidget(QLabel("Meeting templates"))
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self._show_template_preview)
        templates_layout.addWidget(self.template_list, 1)
        self.preview = QLabel("Select a template to preview its next three occurrences.")
        self.preview.setWordWrap(True)
        templates_layout.addWidget(self.preview)
        template_actions = QHBoxLayout()
        for label, callback in (("Add", self.add_template), ("Edit", self.edit_template),
                                ("Pause / Resume", self.toggle_template), ("Delete", self.delete_template)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            template_actions.addWidget(button)
        templates_layout.addLayout(template_actions)
        splitter.addWidget(templates_panel)

        date_panel = QWidget()
        date_layout = QVBoxLayout(date_panel)
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.selectionChanged.connect(self.refresh_occurrences)
        date_layout.addWidget(self.calendar)
        self.occurrence_list = QListWidget()
        self.occurrence_list.itemDoubleClicked.connect(self._open_selected_details)
        self.occurrence_list.currentItemChanged.connect(self._show_occurrence_details)
        date_layout.addWidget(self.occurrence_list, 1)
        self.occurrence_details = QLabel("Select an occurrence to see its details.")
        self.occurrence_details.setWordWrap(True)
        date_layout.addWidget(self.occurrence_details)
        self.occurrence_status = QLabel()
        date_layout.addWidget(self.occurrence_status)
        occurrence_actions = QHBoxLayout()
        self.start_button = QPushButton("Start recording")
        self.start_button.clicked.connect(self.start_selected)
        occurrence_actions.addWidget(self.start_button)
        self.snooze_button = QPushButton("Snooze")
        self.snooze_button.clicked.connect(self.snooze_selected)
        occurrence_actions.addWidget(self.snooze_button)
        self.dismiss_button = QPushButton("Dismiss")
        self.dismiss_button.clicked.connect(self.dismiss_selected)
        occurrence_actions.addWidget(self.dismiss_button)
        self.details_button = QPushButton("Open details")
        self.details_button.clicked.connect(self._open_selected_details)
        occurrence_actions.addWidget(self.details_button)
        date_layout.addLayout(occurrence_actions)
        splitter.addWidget(date_panel)
        splitter.setSizes([360, 560])
        self.refresh()

    def refresh(self):
        self.scheduler.materialize()
        selected_id = self._selected_template_id()
        self.template_list.clear()
        for template in self.repository.list_templates():
            item = QListWidgetItem(f"{'▶' if template['enabled'] else 'Ⅱ'}  {template['title']} · {template['local_start_time']} · {template['timezone']}")
            item.setData(Qt.ItemDataRole.UserRole, template["id"])
            item.setToolTip(f"{', '.join(template['tags']) or 'No tags'} · {template['recurrence_kind']}")
            self.template_list.addItem(item)
            if template["id"] == selected_id:
                self.template_list.setCurrentItem(item)
        if self.template_list.currentItem() is None and self.template_list.count():
            self.template_list.setCurrentRow(0)
        self.refresh_occurrences()

    def refresh_occurrences(self, *_args):
        day = self.calendar.selectedDate().toString("yyyy-MM-dd")
        selected_id = self._selected_occurrence_id()
        self.occurrence_list.clear()
        matching = self.repository.list_occurrences(local_date=day)
        for occurrence in matching:
            tags = occurrence.get("tags") or "[]"
            label = f"{occurrence['scheduled_local']} · {occurrence['title']} · {occurrence['state']}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, occurrence["id"])
            item.setToolTip(f"{occurrence['timezone']} · {tags}")
            self.occurrence_list.addItem(item)
            if occurrence["id"] == selected_id:
                self.occurrence_list.setCurrentItem(item)
        if self.occurrence_list.currentItem() is None and self.occurrence_list.count():
            self.occurrence_list.setCurrentRow(0)
        self.occurrence_status.setText(
            f"{len(matching)} meeting(s) on {day}" if matching else f"No scheduled meetings on {day}"
        )
        self._update_occurrence_actions()

    def _selected_template_id(self):
        item = self.template_list.currentItem() if hasattr(self, "template_list") else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selected_occurrence_id(self):
        item = self.occurrence_list.currentItem() if hasattr(self, "occurrence_list") else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selected_template(self):
        template_id = self._selected_template_id()
        return self.repository.get_template(template_id) if template_id else None

    def _show_template_preview(self, current, _previous=None):
        if not current:
            self.preview.setText("Select a template to preview its next three occurrences.")
            return
        template = self.repository.get_template(current.data(Qt.ItemDataRole.UserRole))
        if not template:
            return
        rows = next_occurrences(template, count=3)
        self.preview.setText("Next three: " + (" · ".join(
            f"{row['scheduled_local']} {row['timezone']}" for row in rows
        ) or "No further occurrences"))

    def add_template(self):
        dialog = MeetingTemplateDialog(parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.repository.create_template(dialog.result_data)
            self.refresh()

    def edit_template(self):
        template = self._selected_template()
        if not template:
            return
        dialog = MeetingTemplateDialog(template, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        answer = QMessageBox.question(
            self, "Update future meetings?",
            "Apply the new template to future occurrences that have not started? Pending reminders will be recalculated.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.repository.update_template(template["id"], dialog.result_data, update_future=True)
        self.refresh()

    def toggle_template(self):
        template = self._selected_template()
        if template:
            self.repository.set_enabled(template["id"], not template["enabled"])
            self.refresh()

    def delete_template(self):
        template = self._selected_template()
        if not template:
            return
        answer = QMessageBox.question(
            self, "Delete meeting template",
            "Stop future reminders and archive this template? Started recordings and meeting history will remain.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.repository.archive_template(template["id"])
            self.refresh()

    def start_selected(self):
        occurrence_id = self._selected_occurrence_id()
        if occurrence_id is not None:
            self.start_requested.emit(int(occurrence_id))

    def snooze_selected(self):
        occurrence_id = self._selected_occurrence_id()
        if occurrence_id is None:
            return
        minutes, accepted = QInputDialog.getItem(self, "Snooze reminder", "Snooze for:", ["5", "10", "15"], 1, False)
        if accepted:
            self.scheduler.snooze(int(occurrence_id), int(minutes))
            self.refresh_occurrences()

    def dismiss_selected(self):
        occurrence_id = self._selected_occurrence_id()
        if occurrence_id is not None:
            self.scheduler.dismiss(int(occurrence_id))
            self.refresh_occurrences()

    def _open_selected_details(self, *_args):
        occurrence_id = self._selected_occurrence_id()
        if occurrence_id is not None:
            self._show_occurrence_details(self.occurrence_list.currentItem())
            self.details_requested.emit(int(occurrence_id))

    def _update_occurrence_actions(self):
        occurrence_id = self._selected_occurrence_id()
        occurrence = self.repository.get_occurrence(int(occurrence_id)) if occurrence_id is not None else None
        state = occurrence["state"] if occurrence else None
        can_action = state in ("scheduled", "notified", "snoozed", "missed")
        self.start_button.setEnabled(can_action)
        self.snooze_button.setEnabled(state == "notified")
        self.dismiss_button.setEnabled(can_action)
        self.details_button.setEnabled(occurrence is not None)

    def _show_occurrence_details(self, current, _previous=None):
        if current is None:
            self.occurrence_details.setText("Select an occurrence to see its details.")
            return
        occurrence_id = current.data(Qt.ItemDataRole.UserRole)
        occurrence = self.repository.get_occurrence(int(occurrence_id))
        if not occurrence:
            return
        tags = occurrence.get("tags", [])
        self.occurrence_details.setText(
            f"{occurrence['title']}\n{occurrence['scheduled_local']} · {occurrence['timezone']}\n"
            f"Duration: {int(occurrence['expected_duration_seconds']) // 60} min · "
            f"State: {occurrence['state']} · Tags: {', '.join(tags) or 'None'}"
        )

    def select_occurrence(self, occurrence_id: int):
        occurrence = self.repository.get_occurrence(int(occurrence_id))
        if not occurrence:
            return
        date = QDate.fromString(occurrence["scheduled_local"][:10], "yyyy-MM-dd")
        self.calendar.setSelectedDate(date)
        for index in range(self.occurrence_list.count()):
            item = self.occurrence_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == int(occurrence_id):
                self.occurrence_list.setCurrentItem(item)
                break
