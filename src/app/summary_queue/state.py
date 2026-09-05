"""Mutable, non-Qt execution state for the sequential summary queue."""

from collections import deque
from typing import Any, Deque, Dict, Literal, Optional

from src.app.summary_queue.tasks import task_key


DuplicateState = Literal["running", "queued"]


class QueueExecutionState:
    """Own pending-task ordering and the active task/worker transition."""

    def __init__(self):
        self.pending: Deque[Dict] = deque()
        self.current_task: Optional[Dict] = None
        self.current_worker: Optional[Any] = None
        self.current_task_had_error = False

    @property
    def pending_count(self) -> int:
        return len(self.pending) + (1 if self.current_task else 0)

    def duplicate_state(self, task: Dict) -> Optional[DuplicateState]:
        key = task_key(task)
        if self.current_task and task_key(self.current_task) == key:
            return "running"
        if any(task_key(queued_task) == key for queued_task in self.pending):
            return "queued"
        return None

    def remove_pending_at(self, index: int) -> bool:
        if not 0 <= index < len(self.pending):
            return False
        del self.pending[index]
        return True

    def move_pending(self, from_index: int, to_index: int) -> bool:
        if not (0 <= from_index < len(self.pending) and 0 <= to_index < len(self.pending)):
            return False
        task = self.pending[from_index]
        del self.pending[from_index]
        self.pending.insert(to_index, task)
        return True

    def take_next(self) -> Optional[Dict]:
        if self.current_worker is not None or not self.pending:
            return None
        self.current_task = self.pending.popleft()
        self.current_task_had_error = False
        return self.current_task

    def finish_current(self) -> tuple[Optional[Dict], Optional[Any]]:
        task, worker = self.current_task, self.current_worker
        self.current_task = None
        self.current_worker = None
        self.current_task_had_error = False
        return task, worker

    def cancel_all(self) -> tuple[int, Optional[Dict]]:
        pending_removed, current_task = len(self.pending), self.current_task
        self.pending.clear()
        self.current_worker = None
        self.current_task = None
        self.current_task_had_error = False
        return pending_removed, current_task
