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

import logging
from typing import Dict, Optional, Tuple, Any, List

from PyQt6.QtCore import QObject, pyqtSignal, QSettings, QTimer

from src.app.summary_queue.completion import handle_worker_completion
from src.app.summary_queue.completion_actions import QueueCompletionActionCoordinator
from src.app.summary_queue.admission import QueueTaskAdmissionCoordinator
from src.app.summary_queue.history import QueueHistory
from src.app.summary_queue.helpers import (
    parse_task_extraction_result as _parse_task_extraction_result,
    read_audio_duration_seconds as _read_audio_duration_seconds,
)
from src.app.summary_queue.runtime import collect_runtime_stats, stop_worker
from src.app.summary_queue.execution import QueueWorkerExecutionCoordinator
from src.app.summary_queue.state import QueueExecutionState
from src.app.summary_queue.wait_state import QueueRetryWaitState
from src.app.summary_queue.tasks import normalize_source, task_key
from src.app.summary_queue.worker_factory import build_queue_worker
from src.app.summary_queue.worker_signals import connect_queue_worker_signals
from src.app.summary_queue.worker_lifecycle import start_queue_worker_lifecycle
from src.app.summary_queue.threads import RAGReindexThread
from src.summary_generator import SummaryGenerator
from src.ai_assistant import AIAssistant
from src.database import DBManager
from src.worker_components.engine import is_transcription_fatal_failure
from src.worker_components.transcriber_thread import TranscriberThread


class SummaryTaskQueueManager(QObject):
    """Sequential coordinator for long-running background tasks.

    This manager is the single integration point between UI actions and workers:
    transcription, summaries, task extraction and RAG reindexing all enter here.
    It normalizes deduplication, cancellation, progress/status proxy signals and
    in-session history so the UI can render task state consistently.
    """

    queue_changed = pyqtSignal(int, bool)  # pending_count, is_running
    task_enqueued = pyqtSignal(dict, int)  # task, queue_position
    task_started = pyqtSignal(dict, int)   # task, remaining_pending
    task_finished = pyqtSignal(dict)       # task
    task_failed = pyqtSignal(dict, str)    # task, error message
    task_skipped = pyqtSignal(dict, str)   # task, reason
    task_progress = pyqtSignal(int)        # Proxy for progress (0-100, -1 for indeterminate)
    task_status_update = pyqtSignal(str)   # Proxy for status messages
    wait_state_changed = pyqtSignal(bool, int, str)  # is_waiting, seconds_left, description
    history_changed = pyqtSignal(int)  # number of entries in session history

    def __init__(self, parent=None, persistence=None):
        super().__init__(parent)
        self._state = QueueExecutionState()
        self._zombie_workers = [] 
        self.db = persistence if persistence is not None else DBManager()
        self.rag_engine = None
        self._wait_state = QueueRetryWaitState()
        self._wait_timer = QTimer(self)
        self._wait_timer.setInterval(1000)
        self._wait_timer.timeout.connect(self._tick_wait_timer)
        self._history = QueueHistory(max_entries=300)
        self._execution = QueueWorkerExecutionCoordinator(
            state=self._state,
            history=self._history,
            wait_state=self._wait_state,
            wait_timer=self._wait_timer,
            completion_actions=self._completion_action_coordinator,
            handle_completion=lambda task, result: handle_worker_completion(self.db, task, result),
            append_history=self._append_history,
            emit_progress=self.task_progress.emit,
            emit_status=self.task_status_update.emit,
            emit_skipped=self.task_skipped.emit,
            emit_failed=self.task_failed.emit,
            emit_finished=self.task_finished.emit,
            emit_wait_state=self.wait_state_changed.emit,
            emit_queue_state=self._emit_queue_state,
            start_next=self._start_next_if_idle,
            retain_worker=self._retain_zombie_worker,
            is_fatal_transcription_failure=is_transcription_fatal_failure,
        )
    @property
    def _queue(self):
        """Compatibility view of pending tasks for existing integrations/tests."""
        return self._state.pending

    @property
    def _current_task(self):
        return self._state.current_task

    @_current_task.setter
    def _current_task(self, task):
        self._state.current_task = task

    @property
    def _current_worker(self):
        return self._state.current_worker

    @_current_worker.setter
    def _current_worker(self, worker):
        self._state.current_worker = worker

    @property
    def _current_task_had_error(self):
        return self._state.current_task_had_error

    @_current_task_had_error.setter
    def _current_task_had_error(self, had_error):
        self._state.current_task_had_error = bool(had_error)

    @property
    def current_worker(self):
        return self._current_worker

    @property
    def pending_count(self) -> int:
        return self._state.pending_count

    @property
    def is_running(self) -> bool:
        return self._current_worker is not None

    def get_queue_list(self) -> List[Dict]:
        """Return a list of all tasks in the queue (pending)."""
        return list(self._queue)

    def get_current_task(self) -> Optional[Dict]:
        """Return the currently running task."""
        return self._current_task

    def get_wait_state(self) -> Tuple[bool, int, str]:
        return self._wait_state.snapshot()

    def get_session_history(self) -> List[Dict]:
        """Return session execution history (newest first)."""
        return self._history.newest_first()

    def get_runtime_stats(self) -> Dict[str, int]:
        """Return lightweight runtime counters for queue observability widgets."""
        return collect_runtime_stats(
            has_current_task=self._current_task is not None,
            pending_count=len(self._queue),
            history_entries=self._history.newest_first(),
        )

    def remove_task_at(self, index: int) -> bool:
        """Remove a task from the pending queue at the given index."""
        if self._state.remove_pending_at(index):
            self._emit_queue_state()
            logging.info("Queue: removed pending task at index=%s (remaining=%s).", index, len(self._queue))
            return True
        logging.debug("Queue: remove_task_at ignored invalid index=%s (size=%s).", index, len(self._queue))
        return False

    def move_task(self, from_index: int, to_index: int) -> bool:
        """Move a task within the pending queue."""
        if self._state.move_pending(from_index, to_index):
            self._emit_queue_state()
            logging.info("Queue: moved pending task from %s to %s.", from_index, to_index)
            return True
        logging.debug(
            "Queue: move_task ignored invalid range from=%s to=%s (size=%s).",
            from_index,
            to_index,
            len(self._queue),
        )
        return False

    def enqueue_daily_summary(self, summary_data: Dict) -> bool:
        return self._task_admission_coordinator().enqueue_daily_summary(summary_data)

    def enqueue_recording_summary(self, record_id: int, text: str, title: str, source: str = "manual") -> bool:
        return self._task_admission_coordinator().enqueue_recording_summary(record_id, text, title, source)

    def enqueue_weekly_summary(self, week_sunday: str, text: str, tags_filter: str = "", source: str = "manual") -> bool:
        return self._task_admission_coordinator().enqueue_weekly_summary(week_sunday, text, tags_filter, source)

    def enqueue_task_extraction(self, record_id: int, text: str, tags: str, title: str = "", force: bool = False, source: str = "manual") -> bool:
        return self._task_admission_coordinator().enqueue_task_extraction(
            record_id, text, tags, title, force, source
        )

    def enqueue_transcription(self, record_id: int, audio_path: str, model_size: str = "base", language: str = None, diarization: bool = False, title: str = "", source: str = "manual") -> bool:
        return self._task_admission_coordinator().enqueue_transcription(
            record_id, audio_path, model_size, language, diarization, title, source
        )

    def enqueue_rag_reindex(self, scope: str = "all", source: str = "manual") -> bool:
        return self._task_admission_coordinator().enqueue_rag_reindex(scope, source)

    def set_rag_engine(self, rag_engine) -> None:
        self.rag_engine = rag_engine

    def add_external_trace(self, message: str, task: Optional[Dict] = None, event: str = "trace"):
        msg = str(message or "").strip()
        if not msg:
            return
        payload = dict(task or {})
        if not payload:
            payload = {"type": "transcription"}
        # External traces are intentionally persisted as queue history entries so UI diagnostics stay chronological.
        self._append_history(event, payload, msg)
        self.task_status_update.emit(msg)

    def _enqueue_unique_task(self, task: Dict) -> bool:
        duplicate_state = self._state.duplicate_state(task)
        if duplicate_state == "running":
            self.task_skipped.emit(task, "Task already running.")
            self._append_history("skipped", task, "Task already running.")
            logging.info("Queue: skipped duplicate running task type=%s.", task.get("type"))
            return False

        if duplicate_state == "queued":
            self.task_skipped.emit(task, "Task already queued.")
            self._append_history("skipped", task, "Task already queued.")
            logging.info("Queue: skipped duplicate queued task type=%s.", task.get("type"))
            return False

        self._queue.append(task)
        logging.info("Queue: enqueued task type=%s (pending=%s).", task.get("type"), len(self._queue))
        self.task_enqueued.emit(task, len(self._queue))
        self._append_history("queued", task)
        self._emit_queue_state()
        self._start_next_if_idle()
        return True

    def cancel_all(self):
        worker = self._current_worker
        pending_removed, current_task = self._state.cancel_all()
        logging.info("Queue: cancel_all requested (pending_removed=%s, had_current=%s).", pending_removed, bool(current_task))
        if worker and worker.isRunning():
            stop_worker(worker, log_context="cancel_all")
        self._clear_wait_state()
        self.task_status_update.emit("Queue stopped by user.")
        if current_task:
            self._append_history("cancelled", current_task, "Stopped by user.")
        if pending_removed:
            self._append_history("cleared", {"type": "queue"}, f"Cleared {pending_removed} pending task(s).")
        self._emit_queue_state()

    def cancel_current(self) -> bool:
        if not self._current_worker:
            logging.debug("Queue: cancel_current ignored because no worker is running.")
            return False

        worker = self._current_worker
        task = self._current_task or {}
        stop_worker(worker, log_context="cancel_current")
        logging.info("Queue: stop requested for current task type=%s.", task.get("type"))

        self._clear_wait_state()
        self.task_status_update.emit("Stopping current task...")
        self._append_history("cancel_requested", task, "Stop requested by user.")
        return True

    def _task_key(self, task: Dict) -> Tuple[Any, ...]:
        return task_key(task)

    def _normalize_source(self, source: Optional[str], default: str = "manual") -> str:
        return normalize_source(source, default)

    def _task_admission_coordinator(self) -> QueueTaskAdmissionCoordinator:
        return QueueTaskAdmissionCoordinator(
            self.db,
            submit=self._enqueue_unique_task,
            skip=self._skip_task,
        )

    def _skip_task(self, task: Dict, reason: str) -> None:
        self.task_skipped.emit(task, reason)
        self._append_history("skipped", task, reason)

    def _emit_queue_state(self):
        self.queue_changed.emit(self.pending_count, self._current_worker is not None)

    def _start_next_if_idle(self):
        if self._current_worker is not None:
            logging.debug("Queue: start skipped because a worker is already running.")
            return
        if not self._queue:
            logging.debug("Queue: start skipped because pending queue is empty.")
            self._emit_queue_state()
            return

        task = self._state.take_next()
        if task is None:
            return
        self._clear_wait_state()

        # Exactly one worker is started at a time; this is the sequential execution gate.
        task_type = task["type"]
        logging.info("Queue: starting task type=%s.", task_type)

        try:
            worker = build_queue_worker(
                task,
                parent=self,
                db=self.db,
                rag_engine=self.rag_engine,
                on_worker_completed=self._on_worker_completed,
                on_generator_recording_summary_completed=self._on_generator_recording_summary_completed,
                on_generator_progress=self._on_generator_progress,
                on_progress_emit=self.task_progress.emit,
                on_status_update=self._on_worker_status_update,
                settings_cls=QSettings,
                summary_generator_cls=SummaryGenerator,
                transcriber_cls=TranscriberThread,
                rag_reindex_thread_cls=RAGReindexThread,
                ai_assistant_cls=AIAssistant,
            )

            connect_queue_worker_signals(
                worker,
                task_type=task_type,
                on_error=self._on_worker_error,
                on_finished=self._on_worker_completely_finished,
                on_status_update=self._on_worker_status_update,
                on_retry_wait=self._on_worker_retry_wait,
            )
            start_queue_worker_lifecycle(
                worker=worker,
                task=task,
                pending_remaining=len(self._queue),
                set_current_worker=lambda w: setattr(self, "_current_worker", w),
                emit_task_started=self.task_started.emit,
                append_history=self._append_history,
                emit_queue_state=self._emit_queue_state,
            )
        except Exception as e:
            logging.error("Queue: failed to start worker for task type=%s: %s", task_type, e, exc_info=True)
            self._on_worker_error(str(e))

    def _on_generator_progress(self, current, total):
        self._execution.on_generator_progress(current, total)

    def _on_generator_recording_summary_completed(self, record_id: int, title: str):
        self._execution.on_generator_recording_summary_completed(record_id, title)

    def _on_worker_completed(self, result: Any = None):
        self._execution.on_worker_completed(result)

    def _apply_completion_action(self, action: Dict):
        """Compatibility delegate for integrations using the former private hook."""
        self._completion_action_coordinator().apply((action,))

    def _completion_action_coordinator(self) -> QueueCompletionActionCoordinator:
        return QueueCompletionActionCoordinator(
            self.db,
            enqueue_task_extraction=self.enqueue_task_extraction,
            enqueue_recording_summary=self.enqueue_recording_summary,
            emit_status=self.task_status_update.emit,
        )

    def _on_worker_error(self, error_msg: str):
        self._execution.on_worker_error(error_msg)

    def _on_worker_status_update(self, message: str):
        before = len(self._history)
        self._execution.on_worker_status_update(message)
        if len(self._history) != before:
            self.history_changed.emit(len(self._history))

    def _on_worker_completely_finished(self):
        self._execution.on_worker_completely_finished()

    def _on_worker_retry_wait(self, delay_seconds: float, attempt: int, total_attempts: int, error_text: str):
        self._execution.on_worker_retry_wait(delay_seconds, attempt, total_attempts, error_text)

    def _tick_wait_timer(self):
        self._execution.tick_wait_state()

    def _clear_wait_state(self):
        self._execution.clear_wait_state()

    def _retain_zombie_worker(self, worker):
        self._zombie_workers.append(worker)
        if len(self._zombie_workers) > 5:
            self._zombie_workers.pop(0)

    def _append_history(self, event: str, task: Dict, message: str = ""):
        self._history.append(event, task, message)
        self.history_changed.emit(len(self._history))
        logging.debug("Queue: history appended event=%s task_type=%s.", event, (task or {}).get("type"))
