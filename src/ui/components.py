# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import hashlib

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                             QPushButton, QSizePolicy, QLineEdit, QCompleter, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt6.QtGui import QIcon, QColor


def _tag_palette(tag: str):
    """Return deterministic colors for a tag name."""
    norm = (tag or "").strip().lower()
    digest = hashlib.md5(norm.encode("utf-8")).hexdigest()
    hue = int(digest[:2], 16) % 360

    base = QColor.fromHsv(hue, 130, 215)
    border = base.darker(145)
    text_color = "#111111" if base.lightness() > 145 else "#ffffff"
    return base.name(), border.name(), text_color


def create_tag_chip(tag: str, width: int | None = 84, height: int = 18, font_size: int = 10, parent=None) -> QLabel:
    """Create a compact colored chip with stable color for a given tag."""
    bg, border, text_color = _tag_palette(tag)
    chip = QLabel(tag, parent)
    chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if width is None:
        metrics = chip.fontMetrics()
        dynamic_width = max(24, metrics.horizontalAdvance(tag) + 14)
        chip.setFixedHeight(height)
        chip.setMinimumWidth(dynamic_width)
    else:
        chip.setFixedSize(width, height)
    chip.setToolTip(tag)
    chip.setStyleSheet(
        f"QLabel {{"
        f"background-color: {bg};"
        f"color: {text_color};"
        f"border: 1px solid {border};"
        f"border-radius: 7px;"
        f"padding: 0px 4px;"
        f"font-size: {font_size}px;"
        f"font-weight: 600;"
        f"}}"
    )
    return chip


class SidebarTaskCompactWidget(QWidget):
    """Compact task row for sidebar accordion: title + tiny tags line."""
    completion_toggled = pyqtSignal(int, bool)
    ROW_HEIGHT = 56

    def __init__(
        self,
        title: str,
        tags: list[str],
        task_id: int | None = None,
        is_completed: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.task_id = task_id
        self._build_ui(title, tags, is_completed)

    def _build_ui(self, title: str, tags: list[str], is_completed: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        top_row = QWidget()
        top_row.setMinimumHeight(22)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        self.complete_check = QCheckBox()
        self.complete_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.complete_check.setChecked(bool(is_completed))
        self.complete_check.setStyleSheet("""
            QCheckBox {
                spacing: 0px;
                padding: 0px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #7f8c8d;
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 0.06);
            }
            QCheckBox::indicator:hover {
                border-color: #b0bec5;
                background-color: rgba(176, 190, 197, 0.18);
            }
            QCheckBox::indicator:checked {
                border-color: #66bb6a;
                background-color: #2e7d32;
                image: none;
            }
            QCheckBox::indicator:checked:hover {
                border-color: #81c784;
                background-color: #388e3c;
            }
        """)
        self.complete_check.toggled.connect(self._on_toggle_completed)
        top_layout.addWidget(self.complete_check, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel((title or "").strip() or "Untitled task")
        self.title_label.setWordWrap(False)
        self.title_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        top_layout.addWidget(self.title_label, 1)
        layout.addWidget(top_row)

        tags_row = QWidget()
        tags_row.setMinimumHeight(16)
        tags_layout = QHBoxLayout(tags_row)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        tags_layout.setSpacing(4)

        self.tag_chips = []
        if tags:
            for tag in tags:
                chip = create_tag_chip(tag, width=None, height=16, font_size=9, parent=self)
                self.tag_chips.append(chip)
                tags_layout.addWidget(chip)
        else:
            no_tags = QLabel("No tags")
            no_tags.setStyleSheet("font-size: 10px; color: #8a8a8a;")
            tags_layout.addWidget(no_tags)
            self.tag_chips.append(no_tags)

        tags_layout.addStretch()
        layout.addWidget(tags_row)
        self.setFixedHeight(self.ROW_HEIGHT)

    def _on_toggle_completed(self, checked: bool):
        if isinstance(self.task_id, int):
            self.completion_toggled.emit(self.task_id, bool(checked))


class TagsLineEdit(QLineEdit):
    """
    A specialized QLineEdit for entering multiple tags separated by commas.
    Provides autocomplete suggestions after each comma separator.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Etiquetas separadas por coma (ej: Trabajo, Reunión)")
        
        self.all_tags = []
        self.completer_model = QStringListModel()
        
        self.tags_completer = QCompleter()
        self.tags_completer.setModel(self.completer_model)
        self.tags_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.tags_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.tags_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.tags_completer.activated.connect(self.insert_completion)
        self.setCompleter(self.tags_completer)
        
        self.textChanged.connect(self.update_completer_prefix)
    
    def set_tags(self, tags: list):
        """Set the available tags for autocomplete."""
        self.all_tags = tags if tags else []
        self.completer_model.setStringList(self.all_tags)
    
    def get_current_tag_text(self) -> str:
        """Get the text of the tag currently being typed (after the last comma)."""
        text = self.text()
        cursor_pos = self.cursorPosition()
        
        # Find the portion of text from the last comma to cursor
        text_before_cursor = text[:cursor_pos]
        last_comma = text_before_cursor.rfind(',')
        
        if last_comma == -1:
            return text_before_cursor.strip()
        else:
            return text_before_cursor[last_comma + 1:].strip()
    
    def update_completer_prefix(self):
        """Update the completer to filter based on the current tag being typed."""
        current_tag = self.get_current_tag_text()
        
        # Get already selected tags to filter them out from suggestions
        existing_tags = [t.strip().lower() for t in self.text().split(',') if t.strip()]
        current_tag_lower = current_tag.lower()
        
        # Filter out tags that are already entered (except the one being typed)
        available_tags = [
            tag for tag in self.all_tags 
            if tag.lower() not in existing_tags or tag.lower() == current_tag_lower
        ]
        
        self.completer_model.setStringList(available_tags)
        
        # Only show popup if there's something to complete
        if current_tag and len(current_tag) > 0:
            self.tags_completer.setCompletionPrefix(current_tag)
            if self.tags_completer.completionCount() > 0:
                self.tags_completer.complete()
    
    def insert_completion(self, completion: str):
        """Insert the selected completion, preserving previous tags."""
        text = self.text()
        cursor_pos = self.cursorPosition()
        
        # Find the start of the current tag
        text_before_cursor = text[:cursor_pos]
        last_comma = text_before_cursor.rfind(',')
        
        if last_comma == -1:
            # First tag, replace everything before cursor
            prefix = ""
            start_pos = 0
        else:
            # Keep everything up to and including the comma, plus a space
            prefix = text[:last_comma + 1] + " "
            start_pos = last_comma + 1
        
        # Get text after cursor
        text_after_cursor = text[cursor_pos:]
        
        # Build new text
        new_text = prefix + completion + text_after_cursor
        self.setText(new_text)
        
        # Position cursor after the completion
        new_cursor_pos = len(prefix) + len(completion)
        self.setCursorPosition(new_cursor_pos)

class RecordingListItemWidget(QWidget):
    favorite_toggled = pyqtSignal(bool)
    delete_requested = pyqtSignal()
    
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # Info Section - wrap in a widget to control size properly
        info_widget = QWidget()
        # Use Ignored policy so it can shrink below its preferred size
        info_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info_widget.setMinimumWidth(50)  # Ensure at least some text is visible
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        title = self.record.get('title') or self.record.get('created_at')
        self.title_label = QLabel(title)
        self.title_label.setObjectName("record_title")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(self.title_label)
        
        date_str = self.record.get('created_at')
        type_ = self.record.get('type', 'recording')
        if type_ == 'note':
            details = f"📝 {date_str}"
        else:
            duration = self.record.get('duration', 0)
            details = f"{date_str} • {duration:.1f}s"
        self.details_label = QLabel(details)
        self.details_label.setObjectName("record_details")
        self.details_label.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(self.details_label)
        
        # Add the info widget with stretch factor 1 so it takes remaining space
        layout.addWidget(info_widget, 1)
        
        # Buttons - fixed size, no stretch, always visible
        btn_size = 26
        self.fav_btn = QPushButton()
        self.fav_btn.setCheckable(True)
        self.fav_btn.setFixedSize(btn_size, btn_size)
        self.fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fav_btn.setProperty("class", "record-fav-btn")
        # We can use unicode star or icon if available. Let's use unicode for now to avoid asset dependency issues.
        # ★ (U+2605) filled, ☆ (U+2606) empty
        self.update_fav_icon(bool(self.record.get('is_favorite', 0)))
        self.fav_btn.toggled.connect(self.on_fav_toggled)
        self.fav_btn.style().unpolish(self.fav_btn)
        self.fav_btn.style().polish(self.fav_btn)
        layout.addWidget(self.fav_btn, 0, Qt.AlignmentFlag.AlignVCenter)  # stretch factor 0 = don't stretch
        
        self.del_btn = QPushButton("🗑") # Trash bin unicode
        self.del_btn.setFixedSize(btn_size, btn_size)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setProperty("class", "record-del-btn")
        self.del_btn.style().unpolish(self.del_btn)
        self.del_btn.style().polish(self.del_btn)
        self.del_btn.clicked.connect(self.delete_requested.emit)
        layout.addWidget(self.del_btn, 0, Qt.AlignmentFlag.AlignVCenter)  # stretch factor 0 = don't stretch
        
    def update_fav_icon(self, is_fav):
        self.fav_btn.setText("★" if is_fav else "☆")
        self.fav_btn.setChecked(is_fav)
        
    def on_fav_toggled(self, checked):
        self.update_fav_icon(checked)
        self.favorite_toggled.emit(checked)


class SummaryListItemWidget(QWidget):
    """Widget for displaying daily/weekly summaries in the list."""
    
    def __init__(self, summary_data, parent=None):
        super().__init__(parent)
        self.summary_data = summary_data
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Info Section
        info_widget = QWidget()
        info_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info_widget.setMinimumWidth(50)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        type_ = self.summary_data.get('type', 'daily')
        if type_ == 'daily':
            date_str = self.summary_data.get('date')
            title = f"📅 Daily Summary"
            subtitle = date_str
            # Icon or color distinction could be added here
        else:
            week_date = self.summary_data.get('week_start')
            title = f"Week Summary"
            subtitle = f"Week ending {week_date}"
            
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;") # Green for summaries
        info_layout.addWidget(self.title_label)
        
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #888;")
        info_layout.addWidget(self.subtitle_label)
        
        layout.addWidget(info_widget, 1)
        
        # We could add delete button specifically for summaries if needed
        # For now, keep it simple.


class TaskRowWidget(QWidget):
    """Custom widget for a task row, used in summary view and tasks board."""
    status_changed = pyqtSignal(int, bool) # task_id, is_completed

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task_id = task.get("id")
        self.is_completed = bool(task.get("is_completed"))
        self.init_ui(task)

    def init_ui(self, task):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Status Button (Checkmark)
        self.status_btn = QPushButton()
        self.status_btn.setFixedSize(24, 24)
        self.status_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_btn.clicked.connect(self._toggle_status)
        self._update_status_icon()
        layout.addWidget(self.status_btn)

        # Content and Source
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        content = (task.get("content") or "").strip()
        self.content_label = QLabel(content)
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        text_layout.addWidget(self.content_label)

        # Source Metadata (origin + tags + date, easy to scan)
        record_title = (task.get("record_title") or "").strip()
        task_origin = (task.get("task_origin") or "").strip()
        if isinstance(task.get("record_id"), int):
            tags_text = (task.get("record_tags") or task.get("tags") or "").strip()
        else:
            tags_text = (task.get("tags") or task.get("record_tags") or "").strip()
        date_str = (task.get("day_date") or (task.get("created_at") or "")[:10]).strip()

        meta_row = QWidget()
        meta_row.setFixedHeight(22)
        meta_layout = QHBoxLayout(meta_row)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(6)

        origin_text = task_origin or record_title
        self.origin_label = QLabel(f"Origin: {origin_text}" if origin_text else "")
        self.origin_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #8ec5ff;")
        self.origin_label.setFixedHeight(18)
        self.origin_label.setVisible(bool(origin_text))
        if origin_text:
            meta_layout.addWidget(self.origin_label)

        tag_values = [t.strip() for t in tags_text.split(",") if t.strip()]
        for tag in tag_values:
            meta_layout.addWidget(self._create_tag_chip(tag))

        self.source_label = QLabel(f"Date: {date_str}" if date_str else "")
        self.source_label.setStyleSheet("font-size: 11px; color: #888;")
        self.source_label.setFixedHeight(18)
        self.source_label.setVisible(bool(date_str))
        if date_str:
            meta_layout.addWidget(self.source_label)

        meta_layout.addStretch()
        meta_row.setVisible(bool(origin_text or tag_values or date_str))
        text_layout.addWidget(meta_row)

        layout.addLayout(text_layout, 1)

        # Apply initial visual state
        self._apply_visual_state()

    def _toggle_status(self):
        self.is_completed = not self.is_completed
        self._update_status_icon()
        self._apply_visual_state()
        self.status_changed.emit(self.task_id, self.is_completed)

    def _update_status_icon(self):
        if self.is_completed:
            self.status_btn.setText("✔")
            self.status_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.status_btn.setText("")
            self.status_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 2px solid #555;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    border-color: #2196F3;
                }
            """)

    def _apply_visual_state(self):
        font = self.content_label.font()
        font.setStrikeOut(self.is_completed)
        self.content_label.setFont(font)
        
        if self.is_completed:
            self.content_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #888;")
        else:
            self.content_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        
        # Use property for styling if needed in stylesheets
        self.setProperty("completed", self.is_completed)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_completed(self, is_completed):
        """Programmatically set the completion status."""
        if self.is_completed != is_completed:
            self.is_completed = is_completed
            self._update_status_icon()
            self._apply_visual_state()

    def _create_tag_chip(self, tag: str) -> QLabel:
        return create_tag_chip(tag, width=84, height=18, font_size=10, parent=self)
