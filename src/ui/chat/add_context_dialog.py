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

"""Dialog used by ChatWidget to add notebook, tag, or date context."""

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class AddContextDialog(QDialog):
    def __init__(self, db_manager, notebook_db, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.notebook_db = notebook_db
        self.selected_context = None

        self.setWindowTitle("Add Context")
        self.resize(400, 500)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        self.nb_list = QListWidget()
        self.load_notebooks()
        self.tabs.addTab(self.nb_list, "Notebooks")

        self.tag_list = QListWidget()
        self.load_tags()
        self.tabs.addTab(self.tag_list, "Tags")

        date_widget = QWidget()
        date_layout = QVBoxLayout(date_widget)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(datetime.now().date())
        date_layout.addWidget(QLabel("Select Date:"))
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        self.tabs.addTab(date_widget, "Date")

        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_notebooks(self):
        notebooks = self.notebook_db.get_notebooks()
        for nb in notebooks:
            item = QListWidgetItem(f"📓 {nb['name']}")
            item.setData(Qt.ItemDataRole.UserRole, {"type": "notebook", "value": nb["id"], "label": nb["name"]})
            self.nb_list.addItem(item)

    def load_tags(self):
        tags = self.db.get_all_tags()
        for tag in tags:
            item = QListWidgetItem(f"🏷 {tag}")
            item.setData(Qt.ItemDataRole.UserRole, {"type": "tag", "value": tag, "label": tag})
            self.tag_list.addItem(item)

    def on_accept(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            item = self.nb_list.currentItem()
            if item:
                self.selected_context = item.data(Qt.ItemDataRole.UserRole)
        elif idx == 1:
            item = self.tag_list.currentItem()
            if item:
                self.selected_context = item.data(Qt.ItemDataRole.UserRole)
        elif idx == 2:
            date_str = self.date_edit.date().toString("yyyy-MM-dd")
            self.selected_context = {"type": "date", "value": date_str, "label": date_str}

        if self.selected_context:
            self.accept()
        else:
            self.reject()
