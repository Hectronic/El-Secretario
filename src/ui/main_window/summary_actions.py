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


class SummaryActionsCoordinator:
    """Own summary-specific action flows."""

    def __init__(self, window):
        self.window = window

    def regenerate_summary(self, summary_data):
        date = summary_data.get("date")
        if not date:
            return
        payload = dict(summary_data or {})
        payload.setdefault("source", "welcome")
        self.window.summary_task_queue.enqueue_daily_summary(payload)
