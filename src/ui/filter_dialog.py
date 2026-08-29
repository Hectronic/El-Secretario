# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

"""Dialog used to select chat filters by date and tags."""

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class FilterDialog(QDialog):
    def __init__(self, all_tags, current_date=None, current_tags=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chat Filters")
        self.resize(300, 400)

        layout = QVBoxLayout(self)

        self.date_check = QCheckBox("Filter by Date")
        layout.addWidget(self.date_check)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setEnabled(False)
        layout.addWidget(self.date_edit)

        self.date_check.toggled.connect(self.date_edit.setEnabled)

        if current_date:
            self.date_check.setChecked(True)
            self.date_edit.setDate(QDate.fromString(current_date, "yyyy-MM-dd"))

        layout.addWidget(QLabel("Filter by Tags:"))
        self.tag_list = QListWidget()
        for tag in all_tags:
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if current_tags and tag in current_tags:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            self.tag_list.addItem(item)
        layout.addWidget(self.tag_list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_filters(self):
        date_str = None
        if self.date_check.isChecked():
            date_str = self.date_edit.date().toString("yyyy-MM-dd")

        tags = []
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                tags.append(item.text())

        return {"date": date_str, "tags": tags}
