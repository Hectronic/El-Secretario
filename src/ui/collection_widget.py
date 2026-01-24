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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QListWidget, QListWidgetItem, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from src.database import DBManager

class CollectionWidget(QWidget):
    open_recording = pyqtSignal(int)
    start_chat = pyqtSignal(str)

    def __init__(self, tag, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.db = DBManager()
        self.init_ui()
        self.load_recordings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel(f"Collection: {self.tag}")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.chat_btn = QPushButton("Chat with this Collection")
        self.chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.chat_btn.clicked.connect(lambda: self.start_chat.emit(self.tag))
        header_layout.addWidget(self.chat_btn)
        
        layout.addLayout(header_layout)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Recordings List
        layout.addWidget(QLabel("Recordings in this collection:"))
        
        self.recordings_list = QListWidget()
        self.recordings_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #2b2b2b;
                color: #eeeeee;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #3a3a3a;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
        """)
        self.recordings_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.recordings_list)

    def load_recordings(self):
        self.recordings_list.clear()
        records = self.db.fetch_all(tag_filter=self.tag)
        
        if not records:
            item = QListWidgetItem("No recordings found in this collection.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.recordings_list.addItem(item)
            return

        for record in records:
            title = record['title'] if record['title'] else record['created_at']
            duration = f"{record['duration']:.1f}s"
            item_text = f"{title} ({duration})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, record['id'])
            self.recordings_list.addItem(item)

    def on_item_clicked(self, item):
        record_id = item.data(Qt.ItemDataRole.UserRole)
        if record_id:
            self.open_recording.emit(record_id)
