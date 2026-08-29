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

from PyQt6.QtCore import Qt


class HistoryNavigationActionsCoordinator:
    """Own history-list click navigation behavior."""

    def __init__(self, window):
        self.window = window

    def on_history_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        type_ = data.get("type", "recording")

        if type_ == "recording":
            self.window.open_recording_tab(data["id"])
        elif type_ == "note":
            self.window.open_note_tab(data["id"])
        else:
            self.window.open_summary_tab(data)
