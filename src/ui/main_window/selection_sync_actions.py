# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from PyQt6.QtCore import QDate


class SelectionSyncActionsCoordinator:
    """Own selection synchronization from Week Details tab to sidebar state."""

    def __init__(self, window):
        self.window = window

    def on_tab_selection_sync(self, monday, date_str, tag=None):
        self.window.current_week_monday = monday if monday.isValid() else None
        self.window.current_date_filter = date_str

        self.window.calendar.blockSignals(True)
        if date_str:
            target = QDate.fromString(date_str, "yyyy-MM-dd")
            self.window.calendar.setSelectedDate(target)
        self.window.calendar.blockSignals(False)

        if tag:
            idx = self.window.tag_filter_combo.findText(tag)
            if idx >= 0:
                self.window.tag_filter_combo.blockSignals(True)
                self.window.tag_filter_combo.setCurrentIndex(idx)
                self.window.tag_filter_combo.blockSignals(False)
        elif tag == "":
            self.window.tag_filter_combo.blockSignals(True)
            self.window.tag_filter_combo.setCurrentIndex(0)
            self.window.tag_filter_combo.blockSignals(False)

        self.window.update_calendar_visuals()
        self.window.request_sidebar_reload(include_tags=True, include_history=True)
        self.window.sync_active_tabs()
