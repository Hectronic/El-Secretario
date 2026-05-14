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


def start_queue_worker_lifecycle(
    *,
    worker,
    task,
    pending_remaining: int,
    set_current_worker,
    emit_task_started,
    append_history,
    emit_queue_state,
):
    set_current_worker(worker)
    emit_task_started(task, pending_remaining)
    append_history("started", task)
    emit_queue_state()
    worker.start()
