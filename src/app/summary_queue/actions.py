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
# along with this program.  See <https://www.gnu.org/licenses/>.

from typing import Protocol


class _QueueLike(Protocol):
    pending_count: int
    is_running: bool

    def move_task(self, from_index: int, to_index: int) -> bool: ...
    def remove_task_at(self, index: int) -> bool: ...
    def cancel_current(self) -> bool: ...
    def cancel_all(self) -> None: ...


class QueueActionCoordinator:
    """Thin non-Qt action layer used by queue widget controls."""

    def __init__(self, task_queue: _QueueLike):
        self.task_queue = task_queue

    def move_up(self, row: int) -> int:
        if row <= 0:
            return row
        if self.task_queue.move_task(row, row - 1):
            return row - 1
        return row

    def move_down(self, row: int, count: int) -> int:
        if row < 0 or row >= count - 1:
            return row
        if self.task_queue.move_task(row, row + 1):
            return row + 1
        return row

    def remove_selected(self, row: int) -> bool:
        if row < 0:
            return False
        return bool(self.task_queue.remove_task_at(row))

    def clear_pending(self) -> int:
        removed = 0
        # pending_count includes the running task; we only clear pending entries.
        while self.task_queue.pending_count > (1 if self.task_queue.is_running else 0):
            if not self.task_queue.remove_task_at(0):
                break
            removed += 1
        return removed

    def stop_current(self) -> bool:
        return bool(self.task_queue.cancel_current())

    def stop_all(self) -> None:
        self.task_queue.cancel_all()
