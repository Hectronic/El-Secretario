from collections import deque
from typing import Deque, Dict, Optional, Tuple, Any, List

from PyQt6.QtCore import QObject, pyqtSignal, QSettings, QTimer

from src.summary_generator import SummaryGenerator
from src.ai_assistant import AIAssistant
from src.database import DBManager
from src.worker import TranscriberThread


class SummaryTaskQueueManager(QObject):
    """
    Centralized queue for background tasks: transcription, summaries, task extraction.
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
        self._wait_remaining_seconds = 0
        self._wait_description = ""
        self._wait_timer = QTimer(self)
        self._wait_timer.setInterval(1000)
        self._wait_timer.timeout.connect(self._tick_wait_timer)
        self._session_history: Deque[Dict[str, Any]] = deque(maxlen=300)
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

        # Before daily summary, ensure every unsummarized recording gets its own summary.
        # This keeps daily/weekly layers coherent when users trigger day regeneration.
        try:
            pending_records = self.db.get_records_without_summary()
            for rec in pending_records:
                rec_id = rec.get("id")
                if not isinstance(rec_id, int):
                    continue
                rec_text = self.db.compose_ai_text(rec.get("transcription", ""), rec.get("recording_notes", ""))
                if not rec_text.strip():
                    continue
                rec_title = (rec.get("title") or f"Recording {rec_id}").strip()
                self.enqueue_recording_summary(rec_id, rec_text, rec_title)
        except Exception:
            pass

        task = {
            "type": "daily_summary",
            "date": date,
            "tags_filter": summary_data.get("tags_filter") or "",
        }
        return self._enqueue_unique_task(task)

    def enqueue_recording_summary(self, record_id: int, text: str, title: str) -> bool:
        task = {
            "type": "summary", 
            "record_id": record_id,
            "text": text,
            "title": title
        }
        return self._enqueue_unique_task(task)

    def enqueue_weekly_summary(self, week_sunday: str, text: str, tags_filter: str = "") -> bool:
        task = {
            "type": "weekly_summary",
            "date": week_sunday,
            "text": text,
            "tags_filter": tags_filter
        }
        return self._enqueue_unique_task(task)

    def enqueue_task_extraction(self, record_id: int, text: str, tags: str, title: str = "") -> bool:
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
        }
        return self._enqueue_unique_task(task)

    def enqueue_transcription(self, record_id: int, audio_path: str, model_size: str = "base", language: str = None, diarization: bool = False, title: str = "") -> bool:
        task = {
            "type": "transcription",
            "record_id": record_id,
            "audio_path": audio_path,
            "model_size": model_size,
            "language": language,
            "diarization": diarization,
            "title": title
        }
        return self._enqueue_unique_task(task)

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
                self._current_worker.wait(3000)
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
        )

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
                worker.all_tasks_finished.connect(lambda *args: self._on_worker_completed())
                worker.progress.connect(self._on_generator_progress)
            elif task_type == "transcription":
                settings = QSettings("Hectronic", "Secretario")
                hf_token = settings.value("hf_token", "")
                force_cpu = settings.value("force_cpu", False, type=bool)
                compute_type = settings.value("compute_type", "int8")
                if compute_type == "auto": compute_type = None
                
                # Get duration
                import soundfile as sf
                duration = 0
                try:
                    f = sf.SoundFile(task["audio_path"])
                    duration = len(f) / f.samplerate
                except: pass

                worker = TranscriberThread(
                    task["audio_path"], 
                    model_size=task["model_size"], 
                    compute_type=compute_type, 
                    language=task["language"], 
                    hf_token=hf_token, 
                    enable_diarization=task["diarization"], 
                    total_duration=duration, 
                    force_cpu=force_cpu
                )
                worker.finished.connect(self._on_worker_completed)
                worker.progress.connect(self.task_progress.emit)
                worker.status_update.connect(self.task_status_update.emit)
            else:
                worker = AIAssistant("", task_type, task.get("text", ""))
                worker.task_completed.connect(lambda t_type, result: self._on_worker_completed(result))
                self.task_progress.emit(-1)
                
            self._current_worker = worker
            worker.error.connect(self._on_worker_error)
            worker.finished.connect(self._on_worker_completely_finished)
            if hasattr(worker, "status_update"):
                worker.status_update.connect(self.task_status_update.emit)
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
                        )
                elif t_type == "weekly_summary":
                    self.db.save_weekly_summary(task["date"], str(result), task.get("tags_filter"))
                elif t_type == "task_extraction":
                    import json, re
                    clean_result = str(result).strip()
                    match = re.search(r'(\[.*\])', clean_result, re.DOTALL)
                    if match: clean_result = match.group(1)
                    try:
                        tasks = json.loads(clean_result)
                        if isinstance(tasks, list):
                            self.db.delete_tasks_by_record(task["record_id"])
                            for t_content in tasks:
                                if isinstance(t_content, str) and t_content.strip():
                                    self.db.save_task(task["record_id"], t_content.strip(), task.get("tags"))
                    except: pass
                elif t_type == "transcription":
                    # result is a dict from TranscriberThread
                    text = result["text"]
                    self.db.update_transcription(task["record_id"], text, is_diarized=result.get("is_diarized", False), transcription_model=result.get("model_size"))
                    # Auto chain summary
                    ai_text = self.db.get_record_ai_text(task["record_id"])
                    self.enqueue_recording_summary(task["record_id"], ai_text, task.get("title", ""))
            except Exception as e:
                logging.error(f"Queue persistence error: {e}", exc_info=True)

    def _on_worker_error(self, error_msg: str):
        task = self._current_task or {}
        self._clear_wait_state()
        self._current_task_had_error = True
        self._append_history("failed", task, str(error_msg or "Unknown error"))
        self.task_failed.emit(task, str(error_msg or "Unknown error"))

    def _on_worker_completely_finished(self):
        task = self._current_task
        worker = self._current_worker
        self._current_worker = None
        self._current_task = None
        self._clear_wait_state()
        if task:
            if not self._current_task_had_error:
                self._append_history("finished", task)
            self.task_finished.emit(task)
        self._current_task_had_error = False
        if worker:
            worker.deleteLater()
            self._zombie_workers.append(worker)
            if len(self._zombie_workers) > 5: self._zombie_workers.pop(0)
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
