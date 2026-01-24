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
                             QListWidget, QListWidgetItem, QInputDialog, QMessageBox, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
from src.ui.styles import LIST_WIDGET_STYLE

class NotebookListItemWidget(QWidget):
    delete_requested = pyqtSignal()
    chat_requested = pyqtSignal()

    def __init__(self, notebook, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Chat Button (Left side)
        chat_btn = QPushButton("💬")
        chat_btn.setFixedSize(30, 30)
        chat_btn.setToolTip("Chat with this notebook")
        chat_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2196F3;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #E3F2FD;
                border-radius: 15px;
            }
        """)
        chat_btn.clicked.connect(self.chat_requested.emit)
        layout.addWidget(chat_btn)
        
        name_label = QLabel(notebook['name'])
        name_label.setStyleSheet("font-size: 16px; margin-left: 5px;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(30, 30)
        del_btn.setToolTip("Delete notebook")
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #f44336;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #FFEBEE;
                border-radius: 15px;
            }
        """)
        del_btn.clicked.connect(self.delete_requested.emit)
        layout.addWidget(del_btn)

class NotebooksListWidget(QWidget):
    notebook_opened = pyqtSignal(int, str)  # id, name
    chat_requested = pyqtSignal(int, str)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()
        self.load_notebooks()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("My Notebooks")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        new_btn = QPushButton("+ New Notebook")
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        new_btn.clicked.connect(self.create_notebook)
        header_layout.addWidget(new_btn)
        
        layout.addLayout(header_layout)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(LIST_WIDGET_STYLE)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.list_widget)

    def load_notebooks(self):
        self.list_widget.clear()
        notebooks = self.db.get_notebooks()
        
        for nb in notebooks:
            item = QListWidgetItem(self.list_widget)
            widget = NotebookListItemWidget(nb)
            widget.delete_requested.connect(lambda n=nb: self.delete_notebook(n))
            widget.chat_requested.connect(lambda n=nb: self.chat_requested.emit(n['id'], n['name']))
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            item.setData(Qt.ItemDataRole.UserRole, nb)

    def create_notebook(self):
        name, ok = QInputDialog.getText(self, "New Notebook", "Notebook Name:")
        if ok and name.strip():
            self.db.create_notebook(name.strip())
            self.load_notebooks()

    def on_item_clicked(self, item):
        notebook = item.data(Qt.ItemDataRole.UserRole)
        self.notebook_opened.emit(notebook['id'], notebook['name'])

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
            
        notebook = item.data(Qt.ItemDataRole.UserRole)
        
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        menu = QMenu(self)
        
        chat_action = QAction("Chat", self)
        chat_action.triggered.connect(lambda: self.chat_requested.emit(notebook['id'], notebook['name']))
        menu.addAction(chat_action)
        
        menu.addSeparator()
        
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(lambda: self.rename_notebook(notebook))
        menu.addAction(rename_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_notebook(notebook))
        menu.addAction(delete_action)
        
        menu.exec(self.list_widget.mapToGlobal(pos))

    def rename_notebook(self, notebook):
        new_name, ok = QInputDialog.getText(self, "Rename Notebook", "New Name:", text=notebook['name'])
        if ok and new_name.strip():
            self.db.rename_notebook(notebook['id'], new_name.strip())
            self.load_notebooks()

    def delete_notebook(self, notebook):
        reply = QMessageBox.question(self, "Delete Notebook", 
                                   f"Are you sure you want to delete '{notebook['name']}' and all its notes?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_notebook(notebook['id'])
            self.load_notebooks()
