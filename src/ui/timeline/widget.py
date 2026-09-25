"""Chronological activity view for Pomodoros and notes."""

from __future__ import annotations

from datetime import date, timedelta

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget


def _iso_date(value):
    if value is None:
        return None
    if hasattr(value, "toString"):
        return value.toString("yyyy-MM-dd")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)[:10]


class TimelineWidget(QWidget):
    source_requested = pyqtSignal(str, int)

    def __init__(self, persistence, parent=None):
        super().__init__(parent)
        self.db = persistence
        self._offset = 0
        self._page_size = 50
        self._filters = (None, None, None)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Activity timeline"))
        self.show_breaks = QCheckBox("Show breaks")
        self.show_breaks.toggled.connect(self.refresh)
        layout.addWidget(self.show_breaks)
        self.list_widget = QListWidget()
        self.list_widget.itemActivated.connect(self._open_item)
        layout.addWidget(self.list_widget)
        footer = QHBoxLayout()
        self.status_label = QLabel()
        footer.addWidget(self.status_label)
        footer.addStretch()
        self.more_button = QPushButton("Load more")
        self.more_button.clicked.connect(self.load_more)
        footer.addWidget(self.more_button)
        layout.addLayout(footer)
        self.refresh()

    def set_global_filters(self, week_monday=None, date_filter=None, tag=None):
        day = _iso_date(date_filter)
        monday = _iso_date(week_monday)
        if monday:
            start = monday
            end = (date.fromisoformat(monday) + timedelta(days=6)).isoformat()
            if day and start <= day <= end:
                end = day
        else:
            start = end = day
        filters = (start, end, None if tag in (None, "", "All") else tag)
        if filters != self._filters:
            self._filters = filters
            self.refresh()

    def refresh(self):
        self._offset = 0
        self.list_widget.clear()
        self.load_more()

    def load_more(self):
        start, end, tag = self._filters
        rows = self.db.fetch_timeline(start_date=start, end_date=end, tag=tag,
                                      limit=self._page_size, offset=self._offset,
                                      show_breaks=self.show_breaks.isChecked())
        for event in rows:
            label = f"{event['occurred_at'][:16]}  ·  {event['title_snapshot']}  ·  {event['event_type'].replace('_', ' ')}"
            if event["display_tags"]:
                label += "  [" + ", ".join(event["display_tags"]) + "]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, (event["event_type"], event["source_id"]))
            self.list_widget.addItem(item)
        self._offset += len(rows)
        self.more_button.setEnabled(len(rows) == self._page_size)
        self.status_label.setText(f"{self.list_widget.count()} activities" if self._offset else "No activity matches these filters")

    def _open_item(self, item):
        event_type, source_id = item.data(Qt.ItemDataRole.UserRole)
        self.source_requested.emit(event_type, source_id)
