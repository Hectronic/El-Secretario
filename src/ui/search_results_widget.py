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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget, 
                             QListWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal

class SearchResultsWidget(QWidget):
    result_clicked = pyqtSignal(int) # Emits record_id

    def __init__(self, query, parent=None):
        super().__init__(parent)
        self.query = query
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        self.header_label = QLabel(f"Search Results for: '{self.query}'")
        self.header_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(self.header_label)
        
        # Results List
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #444;
                border-radius: 5px;
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
        self.results_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.results_list)

    def display_results(self, results):
        self.results_list.clear()
        if not results:
            self.results_list.addItem("No results found.")
            return
            
        self.header_label.setText(f"Search Results for: '{self.query}' ({len(results)} found)")
        
        for res in results:
            title = res['metadata'].get('title', 'Untitled')
            date = res['metadata'].get('date', 'Unknown Date')
            score = 1 - res['distance']
            snippet = res['text'][:200].replace('\n', ' ')
            
            item_text = f"{title} ({date}) - Score: {score:.2f}\n{snippet}..."
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, res['id'])
            self.results_list.addItem(item)

    def on_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.result_clicked.emit(int(data))
