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
                             QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

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
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #eeeeee;")
        info_layout.addWidget(self.title_label)
        
        date_str = self.record.get('created_at')
        duration = self.record.get('duration', 0)
        details = f"{date_str} • {duration:.1f}s"
        self.details_label = QLabel(details)
        self.details_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
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
