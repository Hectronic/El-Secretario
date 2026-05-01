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
import json
import logging
import re
from typing import Deque, Dict, Optional, Tuple, Any, List

from PyQt6.QtCore import QObject, pyqtSignal, QSettings, QTimer, QThread

from src.summary_generator import SummaryGenerator
from src.ai_assistant import AIAssistant
from src.database import DBManager
from src.worker import TranscriberThread


def _read_audio_duration_seconds(audio_path: str) -> float:
    """Best-effort duration probe used to scale transcription progress."""
    try:
        import soundfile as sf

        with sf.SoundFile(audio_path) as audio_file:
            return len(audio_file) / audio_file.samplerate
    except Exception as e:
        logging.warning("Could not read audio duration for queued transcription %s: %s", audio_path, e)
        return 0.0


def _parse_task_extraction_result(raw_result: Any) -> list[str]:
    """Parse the AI task-extraction response into clean task strings."""
    clean_result = str(raw_result or "").strip()
    match = re.search(r"(\[.*\])", clean_result, re.DOTALL)
    if match:
        clean_result = match.group(1)

    try:
        parsed = json.loads(clean_result)
    except Exception:
        return []

    if not isinstance(parsed, list):
        return []
    return [item.strip() for item in parsed if isinstance(item, str) and item.strip()]


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
        if self.rag is None:
            self.error.emit("RAG engine is not initialized.")
            return

        try:
            records = self.db.fetch_all()
            candidates = []
            for rec in records:
                rec_id = rec.get("id")
                if not isinstance(rec_id, int):
                    continue
                rec_type = str(rec.get("type") or "recording")
                if rec_type not in {"recording", "note"}:
                    continue
                ai_text = self.db.get_record_ai_text(rec_id)
                if not str(ai_text or "").strip():
                    continue
                if self.scope == "missing" and self._is_indexed_in_rag(rec_id):
                    continue
                candidates.append((rec, ai_text))

            total = len(candidates)
            if total == 0:
                self.status_update.emit("RAG reindex: no eligible records found.")
                self.progress.emit(100)
                self.task_completed.emit({"indexed": 0, "skipped": 0, "total": 0})
                return

            indexed = 0
            skipped = 0
            for idx, (rec, ai_text) in enumerate(candidates, start=1):
                if self.isInterruptionRequested():
                    self.status_update.emit("RAG reindex interrupted.")
                    break

                rec_id = rec.get("id")
                title = (rec.get("title") or f"Record {rec_id}").strip()
                metadata = {
                    "title": title,
                    "date": rec.get("created_at") or "",
                    "tags": rec.get("tags") or "",
                    "type": rec.get("type") or "recording",
                }
                try:
                    self.rag.add_document(rec_id, ai_text, metadata=metadata)
                    indexed += 1
                except Exception:
                    skipped += 1

                if idx == 1 or idx % 25 == 0 or idx == total:
                    self.status_update.emit(f"RAG reindex: {idx}/{total}")
                self.progress.emit(int((idx / total) * 100))

            self.task_completed.emit({"indexed": indexed, "skipped": skipped, "total": total})
        except Exception as e:
            self.error.emit(str(e))

    def _is_indexed_in_rag(self, record_id: int) -> bool:
        sid = str(record_id)
        try:
            collection = getattr(self.rag, "collection", None)
            if collection is not None and hasattr(collection, "get"):
                raw = collection.get(ids=[sid], where={"deleted": {"$ne": "1"}})
                return bool(raw and raw.get("ids"))
        except Exception:
            pass

        # Fallback path for collection backends that don't expose `get`.
        try:
            hits = self.rag.search("", n_results=1, ids=[sid])
            return bool(hits)
        except Exception:
            return False


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
        self._session_history: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._current_task_had_error = False
        self._last_status_message = ""

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
        return list(reversed(self._session_history))

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
        date = summary_data.get("date")
        if not date:
            self.task_skipped.emit(summary_data, "Daily summary task missing date.")
            self._append_history("skipped", summary_data, "Daily summary task missing date.")
            return False

        task = {
            "type": "daily_summary",
            "date": date,
            "tags_filter": summary_data.get("tags_filter") or "",
            "source": self._normalize_source(summary_data.get("source"), "manual"),
        }
        return self._enqueue_unique_task(task)

    def enqueue_recording_summary(self, record_id: int, text: str, title: str, source: str = "manual") -> bool:
        task = {
            "type": "summary", 
            "record_id": record_id,
            "text": text,
            "title": title,
            "source": self._normalize_source(source, "manual"),
        }
        return self._enqueue_unique_task(task)

    def enqueue_weekly_summary(self, week_sunday: str, text: str, tags_filter: str = "", source: str = "manual") -> bool:
        task = {
            "type": "weekly_summary",
            "date": week_sunday,
            "text": text,
            "tags_filter": tags_filter,
            "source": self._normalize_source(source, "manual"),
        }
        return self._enqueue_unique_task(task)

    def enqueue_task_extraction(self, record_id: int, text: str, tags: str, title: str = "", force: bool = False, source: str = "manual") -> bool:
        if self.db.has_ai_tasks_for_record(record_id) and not force:
            task = {
                "type": "task_extraction",
                "record_id": record_id,
                "title": (title or f"Recording {record_id}").strip(),
                "source": self._normalize_source(source, "manual"),
            }
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

        task = {
            "type": "task_extraction",
            "record_id": record_id,
            "text": text,
            "tags": tags,
            "title": resolved_title,
            "force": bool(force),
            "source": self._normalize_source(source, "manual"),
        }
        return self._enqueue_unique_task(task)

    def enqueue_transcription(self, record_id: int, audio_path: str, model_size: str = "base", language: str = None, diarization: bool = False, title: str = "", source: str = "manual") -> bool:
        task = {
            "type": "transcription",
            "record_id": record_id,
            "audio_path": audio_path,
            "model_size": model_size,
            "language": language,
            "diarization": diarization,
            "title": title,
            "source": self._normalize_source(source, "manual"),
        }
        return self._enqueue_unique_task(task)

    def enqueue_rag_reindex(self, scope: str = "all", source: str = "manual") -> bool:
        normalized_scope = (scope or "all").strip().lower()
        if normalized_scope not in {"all", "missing"}:
            normalized_scope = "all"
        task = {
            "type": "rag_reindex",
            "title": "RAG Reindex",
            "reindex_scope": normalized_scope,
            "source": self._normalize_source(source, "manual"),
        }
        return self._enqueue_unique_task(task)

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
        return (
            task.get("type", ""),
            task.get("date", ""),
            task.get("record_id", ""),
            task.get("tags_filter", ""),
            task.get("audio_path", ""),
            task.get("reindex_scope", ""),
        )

    def _normalize_source(self, source: Optional[str], default: str = "manual") -> str:
        value = str(source or "").strip().lower().replace(" ", "_")
        return value or default

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
                hf_token = settings.value("hf_token", "")
                force_cpu = settings.value("force_cpu", False, type=bool)
                compute_type = settings.value("compute_type", "auto")
                transcription_backend = settings.value("transcription_backend", "auto")
                if compute_type == "auto":
                    compute_type = None
                
                duration = _read_audio_duration_seconds(task["audio_path"])

                worker = TranscriberThread(
                    task["audio_path"], 
                    model_size=task["model_size"], 
                    compute_type=compute_type, 
                    language=task["language"], 
                    hf_token=hf_token, 
                    enable_diarization=task["diarization"], 
                    total_duration=duration, 
                    force_cpu=force_cpu,
                    backend_preference=transcription_backend,
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
        import logging
        
        if result is not None:
            t_type = task.get("type")
            try:
                if t_type == "summary":
                    self.db.update_ai_content(task["record_id"], summary=str(result))
                    rec = self.db.fetch_record(task["record_id"])
                    if rec:
                        ai_text = self.db.get_record_ai_text(task["record_id"])
                        self.enqueue_task_extraction(
                            task["record_id"],
                            ai_text,
                            rec.get("tags") or "",
                            rec.get("title") or f"Recording {task['record_id']}",
                            source=task.get("source") or "summary",
                        )
                elif t_type == "weekly_summary":
                    self.db.save_weekly_summary(task["date"], str(result), task.get("tags_filter"))
                elif t_type == "task_extraction":
                    tasks = _parse_task_extraction_result(result)
                    if tasks:
                        self.db.delete_ai_tasks_by_record(task["record_id"])
                        for task_content in tasks:
                            self.db.save_task(
                                task["record_id"],
                                task_content,
                                task.get("tags"),
                                is_ai_generated=True,
                            )
                elif t_type == "transcription":
                    # result is a dict from TranscriberThread
                    text = result["text"]
                    self.db.update_transcription(
                        task["record_id"],
                        text,
                        is_diarized=result.get("is_diarized", False),
                        transcription_model=result.get("model_name"),
                    )
                    # Keep pending/batch transcription strictly sequential and lightweight:
                    # do not chain summary/task extraction automatically.
                    if task.get("source") != "batch_process":
                        ai_text = self.db.get_record_ai_text(task["record_id"])
                        self.enqueue_recording_summary(
                            task["record_id"],
                            ai_text,
                            task.get("title", ""),
                            source=task.get("source") or "transcription",
                        )
                elif t_type == "rag_reindex" and isinstance(result, dict):
                    indexed = int(result.get("indexed", 0))
                    skipped = int(result.get("skipped", 0))
                    total = int(result.get("total", 0))
                    scope_label = "missing only" if task.get("reindex_scope") == "missing" else "all records"
                    self.task_status_update.emit(
                        f"RAG reindex ({scope_label}) completed: {indexed}/{total} indexed, {skipped} skipped."
                    )
            except Exception as e:
                logging.error(f"Queue persistence error: {e}", exc_info=True)

    def _on_worker_error(self, error_msg: str):
        task = self._current_task or {}
        self._clear_wait_state()
        self._current_task_had_error = True
        self._append_history("failed", task, str(error_msg or "Unknown error"))
        self.task_failed.emit(task, str(error_msg or "Unknown error"))

    def _on_worker_status_update(self, message: str):
        msg = str(message or "").strip()
        if not msg:
            return
        self.task_status_update.emit(msg)
        current_task = self._current_task or {}
        if not current_task:
            return
        # Avoid adding the same status line repeatedly.
        if msg == self._last_status_message:
            return
        self._last_status_message = msg
        self._append_history("trace", current_task, msg)

    def _on_worker_completely_finished(self):
        task = self._current_task
        worker = self._current_worker
        self._current_worker = None
        self._current_task = None
        self._last_status_message = ""
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
        from datetime import datetime

        snapshot = dict(task or {})
        self._session_history.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "event": str(event or "").strip().lower() or "info",
            "task": snapshot,
            "message": str(message or "").strip(),
        })
        self.history_changed.emit(len(self._session_history))
