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

"""Background update check thread for El Secretario."""

from PyQt6.QtCore import QThread, pyqtSignal
from src.auto_updater import check_for_updates


class UpdateCheckerThread(QThread):
    """Background thread to check for updates without blocking the UI."""

    # Emits (is_behind, requirements_changed, message)
    update_checked = pyqtSignal(bool, bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            is_behind, reqs_changed, msg = check_for_updates(timeout_sec=5)
            self.update_checked.emit(is_behind, reqs_changed, msg)
        except Exception as e:
            self.update_checked.emit(False, False, f"Error checking updates: {e}")
