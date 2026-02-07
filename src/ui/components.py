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

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                             QPushButton, QSizePolicy, QLineEdit, QCompleter)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt6.QtGui import QIcon


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
        
        # Info Section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        title = self.record.get('title') or self.record.get('created_at')
        self.title_label = QLabel(title)
        self.title_label.setObjectName("record_title")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_layout.addWidget(self.title_label)
        
        date_str = self.record.get('created_at')
        duration = self.record.get('duration', 0)
        details = f"{date_str} • {duration:.1f}s"
        self.details_label = QLabel(details)
        self.details_label.setObjectName("record_details")
        self.details_label.setStyleSheet("font-size: 12px;")
        info_layout.addWidget(self.details_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Buttons
        self.fav_btn = QPushButton()
        self.fav_btn.setCheckable(True)
        self.fav_btn.setFixedSize(30, 30)
        self.fav_btn.setStyleSheet("QPushButton { border: none; }")
        # We can use unicode star or icon if available. Let's use unicode for now to avoid asset dependency issues.
        # ★ (U+2605) filled, ☆ (U+2606) empty
        self.update_fav_icon(bool(self.record.get('is_favorite', 0)))
        self.fav_btn.toggled.connect(self.on_fav_toggled)
        layout.addWidget(self.fav_btn)
        
        self.del_btn = QPushButton("🗑") # Trash bin unicode
        self.del_btn.setFixedSize(30, 30)
        self.del_btn.setStyleSheet("QPushButton { border: none; color: #f44336; } QPushButton:hover { background-color: #3a3a3a; border-radius: 15px; }")
        self.del_btn.clicked.connect(self.delete_requested.emit)
        layout.addWidget(self.del_btn)
        
    def update_fav_icon(self, is_fav):
        self.fav_btn.setText("★" if is_fav else "☆")
        self.fav_btn.setStyleSheet(f"QPushButton {{ border: none; color: {'#FFC107' if is_fav else 'gray'}; font-size: 20px; }}")
        self.fav_btn.setChecked(is_fav)
        
    def on_fav_toggled(self, checked):
        self.update_fav_icon(checked)
        self.favorite_toggled.emit(checked)
