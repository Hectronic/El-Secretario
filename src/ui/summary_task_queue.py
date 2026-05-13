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
import logging
from typing import Deque, Dict, Optional, Tuple, Any, List

from PyQt6.QtCore import QObject, pyqtSignal, QSettings, QTimer, QThread

from src.app.summary_queue.completion import handle_worker_completion
from src.app.summary_queue.history import QueueHistory
from src.app.summary_queue.helpers import (
    parse_task_extraction_result as _parse_task_extraction_result,
    read_audio_duration_seconds as _read_audio_duration_seconds,
)
from src.app.summary_queue.rag_reindex import run_rag_reindex
from src.app.summary_queue.tasks import (
    build_daily_summary_task,
    build_rag_reindex_task,
    build_recording_summary_task,
    build_task_extraction_task,
    build_transcription_task,
    build_weekly_summary_task,
    normalize_source,
    task_key,
)
from src.app.summary_queue.workers import build_transcription_worker_kwargs
from src.summary_generator import SummaryGenerator
from src.ai_assistant import AIAssistant
from src.database import DBManager
from src.worker_components.engine import is_transcription_fatal_failure
from src.worker_components.transcriber_thread import TranscriberThread


class RAGReindexThread(QThread):
    """Rebuild RAG entries without blocking the queue manager or UI thread."""

    task_completed = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, db: DBManager, rag_engine, scope: str = "all", parent=None):
        super().__init__(parent)
        self.db = db
        self.rag = rag_engine
        self.scope = (scope or "all").strip().lower()

    def run(self):
        try:
            result = run_rag_reindex(
                self.db,
                self.rag,
                self.scope,
                is_interrupted=self.isInterruptionRequested,
                on_status=self.status_update.emit,
                on_progress=self.progress.emit,
            )
            self.task_completed.emit(result)
        except Exception as e:
            self.error.emit(str(e))


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: Deque[Dict] = deque()
        self._current_task: Optional[Dict] = None
        self._current_worker: Optional[Any] = None
        self._zombie_workers = [] 
        self.db = DBManager()
        self.rag_engine = None
        self._wait_remaining_seconds = 0
        self._wait_description = ""
        self._wait_timer = QTimer(self)
        self._wait_timer.setInterval(1000)
        self._wait_timer.timeout.connect(self._tick_wait_timer)
        self._history = QueueHistory(max_entries=300)
        self._current_task_had_error = False

    @property
    def current_worker(self):
        return self._current_worker

    @property
    def pending_count(self) -> int:
        count = len(self._queue)
        if self._current_task:
            count += 1
        return count

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
        return self._wait_remaining_seconds > 0, int(self._wait_remaining_seconds), self._wait_description

    def get_session_history(self) -> List[Dict]:
        """Return session execution history (newest first)."""
        return self._history.newest_first()

    def get_runtime_stats(self) -> Dict[str, int]:
        """Return lightweight runtime counters for queue observability widgets."""
        stats = {
            "running": 1 if self._current_task is not None else 0,
            "pending": len(self._queue),
            "queued": 0,
            "finished": 0,
            "failed": 0,
            "skipped": 0,
            "cancelled": 0,
            "cleared": 0,
            "trace": 0,
        }
        for entry in self._history.newest_first():
            event = str(entry.get("event") or "").strip().lower()
            if event in stats:
                stats[event] += 1
        return stats

    def remove_task_at(self, index: int) -> bool:
        """Remove a task from the pending queue at the given index."""
        if 0 <= index < len(self._queue):
            del self._queue[index]
            self._emit_queue_state()
            return True
        return False

    def move_task(self, from_index: int, to_index: int) -> bool:
        """Move a task within the pending queue."""
        if 0 <= from_index < len(self._queue) and 0 <= to_index < len(self._queue):
            task = self._queue[from_index]
            del self._queue[from_index]
            self._queue.insert(to_index, task)
            self._emit_queue_state()
            return True
        return False

    def enqueue_daily_summary(self, summary_data: Dict) -> bool:
        task = build_daily_summary_task(summary_data)
        if task is None:
            self.task_skipped.emit(summary_data, "Daily summary task missing date.")
            self._append_history("skipped", summary_data, "Daily summary task missing date.")
            return False
        return self._enqueue_unique_task(task)

    def enqueue_recording_summary(self, record_id: int, text: str, title: str, source: str = "manual") -> bool:
        return self._enqueue_unique_task(
            build_recording_summary_task(record_id, text, title, source)
        )

    def enqueue_weekly_summary(self, week_sunday: str, text: str, tags_filter: str = "", source: str = "manual") -> bool:
        return self._enqueue_unique_task(
            build_weekly_summary_task(week_sunday, text, tags_filter, source)
        )

    def enqueue_task_extraction(self, record_id: int, text: str, tags: str, title: str = "", force: bool = False, source: str = "manual") -> bool:
        if self.db.has_ai_tasks_for_record(record_id) and not force:
            task = build_task_extraction_task(record_id, title=title, source=source)
            self.task_skipped.emit(task, "Tasks already generated for this record.")
            self._append_history("skipped", task, "Tasks already generated for this record.")
            return False

        resolved_title = (title or "").strip()
        if not resolved_title:
            rec = self.db.fetch_record(record_id)
            if isinstance(rec, dict):
                resolved_title = (rec.get("title") or f"Recording {record_id}").strip()
            else:
                resolved_title = f"Recording {record_id}"

        return self._enqueue_unique_task(
            build_task_extraction_task(record_id, text, tags, resolved_title, force, source)
        )

    def enqueue_transcription(self, record_id: int, audio_path: str, model_size: str = "base", language: str = None, diarization: bool = False, title: str = "", source: str = "manual") -> bool:
        return self._enqueue_unique_task(
            build_transcription_task(record_id, audio_path, model_size, language, diarization, title, source)
        )

    def enqueue_rag_reindex(self, scope: str = "all", source: str = "manual") -> bool:
        return self._enqueue_unique_task(build_rag_reindex_task(scope, source))

    def set_rag_engine(self, rag_engine) -> None:
        self.rag_engine = rag_engine

    def add_external_trace(self, message: str, task: Optional[Dict] = None, event: str = "trace"):
        msg = str(message or "").strip()
        if not msg:
            return
        payload = dict(task or {})
        if not payload:
            payload = {"type": "transcription"}
        self._append_history(event, payload, msg)
        self.task_status_update.emit(msg)

    def _enqueue_unique_task(self, task: Dict) -> bool:
        dedupe_key = self._task_key(task)

        if self._current_task and self._task_key(self._current_task) == dedupe_key:
            self.task_skipped.emit(task, "Task already running.")
            self._append_history("skipped", task, "Task already running.")
            return False

        for queued_task in self._queue:
            if self._task_key(queued_task) == dedupe_key:
                self.task_skipped.emit(task, "Task already queued.")
                self._append_history("skipped", task, "Task already queued.")
                return False

        self._queue.append(task)
        self.task_enqueued.emit(task, len(self._queue))
        self._append_history("queued", task)
        self._emit_queue_state()
        self._start_next_if_idle()
        return True

    def cancel_all(self):
        pending_removed = len(self._queue)
        current_task = self._current_task
        self._queue.clear()
        if self._current_worker and self._current_worker.isRunning():
            try:
                if hasattr(self._current_worker, "cancel"):
                    self._current_worker.cancel()
                self._current_worker.requestInterruption()
                self._current_worker.quit()
                if not self._current_worker.wait(15000) and hasattr(self._current_worker, "terminate"):
                    logging.warning("Forcing queue worker shutdown during cancel_all.")
                    self._current_worker.terminate()
                    self._current_worker.wait(5000)
            except Exception:
                pass
        self._current_worker = None
        self._current_task = None
        self._current_task_had_error = False
        self._clear_wait_state()
        self.task_status_update.emit("Queue stopped by user.")
        if current_task:
            self._append_history("cancelled", current_task, "Stopped by user.")
        if pending_removed:
            self._append_history("cleared", {"type": "queue"}, f"Cleared {pending_removed} pending task(s).")
        self._emit_queue_state()

    def cancel_current(self) -> bool:
        if not self._current_worker:
            return False

        worker = self._current_worker
        task = self._current_task or {}
        try:
            if hasattr(worker, "cancel"):
                worker.cancel()
            if hasattr(worker, "requestInterruption"):
                worker.requestInterruption()
            if hasattr(worker, "quit"):
                worker.quit()
            if worker.isRunning() and not worker.wait(15000) and hasattr(worker, "terminate"):
                logging.warning("Forcing queue worker shutdown during cancel_current.")
                worker.terminate()
                worker.wait(5000)
        except Exception:
            pass

        self._clear_wait_state()
        self.task_status_update.emit("Stopping current task...")
        self._append_history("cancel_requested", task, "Stop requested by user.")
        return True

    def _task_key(self, task: Dict) -> Tuple[Any, ...]:
        return task_key(task)

    def _normalize_source(self, source: Optional[str], default: str = "manual") -> str:
        return normalize_source(source, default)

    def _emit_queue_state(self):
        self.queue_changed.emit(self.pending_count, self._current_worker is not None)

    def _start_next_if_idle(self):
        if self._current_worker is not None:
            return
        if not self._queue:
            self._emit_queue_state()
            return

        task = self._queue.popleft()
        self._current_task = task
        self._current_task_had_error = False
        self._clear_wait_state()
        
        task_type = task["type"]
        
        try:
            if task_type == "daily_summary":
                tags_filter = task.get("tags_filter") or None
                worker = SummaryGenerator(
                    generate_daily=True,
                    generate_weekly=False,
                    generate_recordings=True,
                    tags_filter=tags_filter,
                    specific_dates=[task["date"]],
                    exclude_today=False,
                    parent=self,
                )
                worker.recording_summary_completed.connect(self._on_generator_recording_summary_completed)
                worker.all_tasks_finished.connect(lambda *args: self._on_worker_completed())
                worker.progress.connect(self._on_generator_progress)
            elif task_type == "transcription":
                settings = QSettings("Hectronic", "Secretario")
                worker = TranscriberThread(
                    **build_transcription_worker_kwargs(settings, task)
                )
                worker.finished.connect(self._on_worker_completed)
                worker.progress.connect(self.task_progress.emit)
                worker.status_update.connect(self._on_worker_status_update)
            elif task_type == "rag_reindex":
                worker = RAGReindexThread(
                    self.db,
                    self.rag_engine,
                    scope=task.get("reindex_scope", "all"),
                    parent=self,
                )
                worker.task_completed.connect(self._on_worker_completed)
                worker.progress.connect(self.task_progress.emit)
            else:
                worker = AIAssistant("", task_type, task.get("text", ""))
                worker.task_completed.connect(lambda t_type, result: self._on_worker_completed(result))
                self.task_progress.emit(-1)
                
            self._current_worker = worker
            worker.error.connect(self._on_worker_error)
            worker.finished.connect(self._on_worker_completely_finished)
            if hasattr(worker, "status_update") and task_type != "transcription":
                worker.status_update.connect(self._on_worker_status_update)
            if hasattr(worker, "retry_wait"):
                worker.retry_wait.connect(self._on_worker_retry_wait)
            
            self.task_started.emit(task, len(self._queue))
            self._append_history("started", task)
            self._emit_queue_state()
            worker.start()
        except Exception as e:
            import logging
            logging.error(f"Failed to start summary worker: {e}", exc_info=True)
            self._on_worker_error(str(e))

    def _on_generator_progress(self, current, total):
        if total > 0:
            percent = int((current / total) * 100)
            self.task_progress.emit(percent)

    def _on_generator_recording_summary_completed(self, record_id: int, title: str):
        try:
            rec = self.db.fetch_record(int(record_id))
            if not isinstance(rec, dict):
                return
            ai_text = self.db.get_record_ai_text(int(record_id))
            if not str(ai_text or "").strip():
                return
            source = (self._current_task or {}).get("source") or "summary"
            self.enqueue_task_extraction(
                int(record_id),
                ai_text,
                rec.get("tags") or "",
                title or rec.get("title") or f"Recording {record_id}",
                source=source,
            )
        except Exception:
            pass

    def _on_worker_completed(self, result: Any = None):
        task = self._current_task or {}
        if result is None:
            return

        try:
            for action in handle_worker_completion(self.db, task, result):
                self._apply_completion_action(action)
        except Exception as e:
            logging.error(f"Queue persistence error: {e}", exc_info=True)

    def _apply_completion_action(self, action: Dict):
        action_type = action.get("type")
        if action_type == "enqueue_task_extraction":
            self.enqueue_task_extraction(
                action["record_id"],
                action.get("text", ""),
                action.get("tags", ""),
                action.get("title", ""),
                source=action.get("source") or "summary",
            )
        elif action_type == "enqueue_recording_summary":
            self.enqueue_recording_summary(
                action["record_id"],
                action.get("text", ""),
                action.get("title", ""),
                source=action.get("source") or "transcription",
            )
        elif action_type == "status":
            self.task_status_update.emit(action.get("message", ""))

    def _on_worker_error(self, error_msg: str):
        task = self._current_task or {}
        self._clear_wait_state()
        self._current_task_had_error = True
        message = str(error_msg or "Unknown error")
        if task.get("type") == "transcription" and is_transcription_fatal_failure(message):
            self._append_history("skipped", task, message)
            self.task_skipped.emit(task, message)
            self.task_status_update.emit(f"Skipping failed transcription: {message}")
        else:
            self._append_history("failed", task, message)
            self.task_failed.emit(task, message)

    def _on_worker_status_update(self, message: str):
        msg = str(message or "").strip()
        if not msg:
            return
        self.task_status_update.emit(msg)
        current_task = self._current_task or {}
        if not current_task:
            return
        if self._history.append_status_trace_once(current_task, msg):
            self.history_changed.emit(len(self._history))

    def _on_worker_completely_finished(self):
        task = self._current_task
        worker = self._current_worker
        self._current_worker = None
        self._current_task = None
        self._history.clear_status_dedup()
        self._clear_wait_state()
        if task:
            if not self._current_task_had_error:
                self._append_history("finished", task)
            self.task_finished.emit(task)
        self._current_task_had_error = False
        if worker:
            worker.deleteLater()
            self._zombie_workers.append(worker)
            if len(self._zombie_workers) > 5:
                self._zombie_workers.pop(0)
        # Opportunistic cleanup between queued jobs helps long pending runs.
        try:
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
        except Exception:
            pass
        self._emit_queue_state()
        self._start_next_if_idle()

    def _on_worker_retry_wait(self, delay_seconds: float, attempt: int, total_attempts: int, error_text: str):
        wait = max(1, int(round(float(delay_seconds))))
        self._wait_remaining_seconds = wait
        short_error = str(error_text or "").strip().replace("\n", " ")
        if len(short_error) > 120:
            short_error = short_error[:117] + "..."
        self._wait_description = f"Retry {attempt + 1}/{total_attempts} in progress"
        self.wait_state_changed.emit(True, self._wait_remaining_seconds, self._wait_description)
        if not self._wait_timer.isActive():
            self._wait_timer.start()
        self.task_status_update.emit(
            f"Waiting {self._wait_remaining_seconds}s before retry ({attempt + 1}/{total_attempts}). {short_error}"
        )

    def _tick_wait_timer(self):
        if self._wait_remaining_seconds <= 0:
            self._clear_wait_state()
            return
        self._wait_remaining_seconds -= 1
        if self._wait_remaining_seconds <= 0:
            self._clear_wait_state()
            return
        self.wait_state_changed.emit(True, self._wait_remaining_seconds, self._wait_description)

    def _clear_wait_state(self):
        self._wait_remaining_seconds = 0
        self._wait_description = ""
        if self._wait_timer.isActive():
            self._wait_timer.stop()
        self.wait_state_changed.emit(False, 0, "")

    def _append_history(self, event: str, task: Dict, message: str = ""):
        self._history.append(event, task, message)
        self.history_changed.emit(len(self._history))
