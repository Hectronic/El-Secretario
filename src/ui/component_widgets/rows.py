"""Reusable list-row widgets for recordings, summaries, and tasks."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from .tags import create_tag_chip


class RecordingListItemWidget(QWidget):
    favorite_toggled = pyqtSignal(bool)
    delete_requested = pyqtSignal()

    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        info = QWidget()
        info.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info.setMinimumWidth(50)
        column = QVBoxLayout(info)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        self.title_label = QLabel(record.get("title") or record.get("created_at"))
        self.title_label.setObjectName("record_title")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        column.addWidget(self.title_label)
        date = record.get("created_at")
        details = f"📝 {date}" if record.get("type", "recording") == "note" else f"{date} • {record.get('duration', 0):.1f}s"
        self.details_label = QLabel(details)
        self.details_label.setObjectName("record_details")
        self.details_label.setStyleSheet("font-size: 12px;")
        column.addWidget(self.details_label)
        layout.addWidget(info, 1)
        self.fav_btn = QPushButton()
        self.fav_btn.setCheckable(True)
        self.fav_btn.setFixedSize(26, 26)
        self.fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fav_btn.setProperty("class", "record-fav-btn")
        self.update_fav_icon(bool(record.get("is_favorite", 0)))
        self.fav_btn.toggled.connect(self.on_fav_toggled)
        self.fav_btn.style().unpolish(self.fav_btn)
        self.fav_btn.style().polish(self.fav_btn)
        layout.addWidget(self.fav_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self.del_btn = QPushButton("🗑")
        self.del_btn.setFixedSize(26, 26)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setProperty("class", "record-del-btn")
        self.del_btn.style().unpolish(self.del_btn)
        self.del_btn.style().polish(self.del_btn)
        self.del_btn.clicked.connect(self.delete_requested.emit)
        layout.addWidget(self.del_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def update_fav_icon(self, is_fav):
        self.fav_btn.setText("★" if is_fav else "☆")
        self.fav_btn.setChecked(is_fav)

    def on_fav_toggled(self, checked):
        self.update_fav_icon(checked)
        self.favorite_toggled.emit(checked)


class SummaryListItemWidget(QWidget):
    """Widget for displaying daily or weekly summaries in a list."""

    def __init__(self, summary_data, parent=None):
        super().__init__(parent)
        self.summary_data = summary_data
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        info = QWidget()
        info.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info.setMinimumWidth(50)
        column = QVBoxLayout(info)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        daily = summary_data.get("type", "daily") == "daily"
        title = "📅 Daily Summary" if daily else "Week Summary"
        subtitle = summary_data.get("date") if daily else f"Week ending {summary_data.get('week_start')}"
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;")
        column.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #888;")
        column.addWidget(self.subtitle_label)
        layout.addWidget(info, 1)


class TaskRowWidget(QWidget):
    """Task-board row with completion control and source metadata."""

    status_changed = pyqtSignal(int, bool)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task_id = task.get("id")
        self.is_completed = bool(task.get("is_completed"))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        self.status_btn = QPushButton()
        self.status_btn.setFixedSize(24, 24)
        self.status_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_btn.clicked.connect(self._toggle_status)
        layout.addWidget(self.status_btn)
        column = QVBoxLayout()
        column.setSpacing(2)
        self.content_label = QLabel((task.get("content") or "").strip())
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        column.addWidget(self.content_label)
        self._add_metadata(column, task)
        layout.addLayout(column, 1)
        self._update_status_icon()
        self._apply_visual_state()

    def _add_metadata(self, column, task):
        origin = (task.get("task_origin") or task.get("record_title") or "").strip()
        tags = ((task.get("record_tags") or task.get("tags") or "") if isinstance(task.get("record_id"), int) else (task.get("tags") or task.get("record_tags") or "")).strip()
        date = (task.get("day_date") or (task.get("created_at") or "")[:10]).strip()
        meta_row = QWidget()
        meta_row.setFixedHeight(22)
        meta = QHBoxLayout(meta_row)
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(6)
        self.origin_label = QLabel(f"Origin: {origin}" if origin else "")
        self.origin_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #8ec5ff;")
        self.origin_label.setFixedHeight(18)
        self.origin_label.setVisible(bool(origin))
        if origin:
            meta.addWidget(self.origin_label)
        tag_values = [tag.strip() for tag in tags.split(",") if tag.strip()]
        for tag in tag_values:
            meta.addWidget(self._create_tag_chip(tag))
        self.source_label = QLabel(f"Date: {date}" if date else "")
        self.source_label.setStyleSheet("font-size: 11px; color: #888;")
        self.source_label.setFixedHeight(18)
        self.source_label.setVisible(bool(date))
        if date:
            meta.addWidget(self.source_label)
        meta.addStretch()
        meta_row.setVisible(bool(origin or tag_values or date))
        column.addWidget(meta_row)

    def _toggle_status(self):
        self.is_completed = not self.is_completed
        self._update_status_icon()
        self._apply_visual_state()
        self.status_changed.emit(self.task_id, self.is_completed)

    def _update_status_icon(self):
        self.status_btn.setText("✔" if self.is_completed else "")
        if self.is_completed:
            self.status_btn.setStyleSheet("background-color: #4CAF50; color: white; border: none; border-radius: 12px; font-weight: bold;")
        else:
            self.status_btn.setStyleSheet("background-color: transparent; border: 2px solid #555; border-radius: 12px;")

    def _apply_visual_state(self):
        font = self.content_label.font()
        font.setStrikeOut(self.is_completed)
        self.content_label.setFont(font)
        self.content_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #888;" if self.is_completed else "font-size: 14px; font-weight: 500;")
        self.setProperty("completed", self.is_completed)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_completed(self, is_completed):
        if self.is_completed != is_completed:
            self.is_completed = is_completed
            self._update_status_icon()
            self._apply_visual_state()

    def _create_tag_chip(self, tag):
        return create_tag_chip(tag, width=84, height=18, font_size=10, parent=self)
