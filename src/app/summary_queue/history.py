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

from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List


class QueueHistory:
    def __init__(self, max_entries: int = 300):
        self._entries: Deque[Dict[str, Any]] = deque(maxlen=max_entries)
        self._last_status_message = ""

    def __len__(self) -> int:
        return len(self._entries)

    def append(self, event: str, task: Dict, message: str = "") -> Dict[str, Any]:
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "event": str(event or "").strip().lower() or "info",
            "task": dict(task or {}),
            "message": str(message or "").strip(),
        }
        self._entries.append(entry)
        return entry

    def newest_first(self) -> List[Dict[str, Any]]:
        return list(reversed(self._entries))

    def clear_status_dedup(self) -> None:
        self._last_status_message = ""

    def append_status_trace_once(self, task: Dict, message: str) -> bool:
        msg = str(message or "").strip()
        if not msg or msg == self._last_status_message:
            return False
        self._last_status_message = msg
        self.append("trace", task, msg)
        return True

