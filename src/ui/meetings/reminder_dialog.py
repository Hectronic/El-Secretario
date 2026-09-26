"""Non-blocking reminder card with explicit meeting actions."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout


class MeetingReminderDialog(QDialog):
    start_requested = pyqtSignal(int)
    snooze_requested = pyqtSignal(int, int)
    dismiss_requested = pyqtSignal(int)
    details_requested = pyqtSignal(int)

    def __init__(self, occurrence: dict, *, missed_count=0, parent=None):
        super().__init__(parent)
        self.occurrence_id = int(occurrence["id"])
        self.setWindowTitle("Missed meeting" if missed_count else "Meeting reminder")
        self.setModal(False)
        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"<b>{occurrence['title']}</b>"))
        local_time = occurrence.get("scheduled_local", "")
        timezone_name = occurrence.get("timezone", "")
        tags = occurrence.get("tags", [])
        if isinstance(tags, str):
            tags = tags.strip("[]").replace('"', "").split(",") if tags != "[]" else []
        message = f"{local_time} · {timezone_name}\nTags: {', '.join(tag.strip() for tag in tags if tag.strip()) or 'None'}"
        if missed_count:
            message = f"{missed_count} meeting(s) were missed while the app was closed.\nLatest: " + message
        info = QLabel(message)
        info.setWordWrap(True)
        root.addWidget(info)
        actions = QHBoxLayout()
        self.start_button = QPushButton("Start recording")
        self.start_button.clicked.connect(lambda: self.start_requested.emit(self.occurrence_id))
        actions.addWidget(self.start_button)
        self.snooze_button = QPushButton("Snooze")
        snooze_menu = QMenu(self.snooze_button)
        for minutes in (5, 10, 15):
            action = snooze_menu.addAction(f"{minutes} minutes")
            action.triggered.connect(lambda _checked=False, value=minutes: self.snooze_requested.emit(self.occurrence_id, value))
        self.snooze_button.setMenu(snooze_menu)
        actions.addWidget(self.snooze_button)
        self.dismiss_button = QPushButton("Dismiss")
        self.dismiss_button.clicked.connect(lambda: self.dismiss_requested.emit(self.occurrence_id))
        actions.addWidget(self.dismiss_button)
        self.details_button = QPushButton("Open details")
        self.details_button.clicked.connect(lambda: self.details_requested.emit(self.occurrence_id))
        actions.addWidget(self.details_button)
        root.addLayout(actions)
